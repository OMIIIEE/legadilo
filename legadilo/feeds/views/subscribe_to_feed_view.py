import json
from http import HTTPMethod, HTTPStatus

import httpx
from asgiref.sync import sync_to_async
from django.contrib import messages
from django.db import IntegrityError
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from legadilo.utils.decorators import alogin_required

from ...users.typing import AuthenticatedHttpRequest
from .. import constants
from ..forms import CreateFeedForm
from ..models import Feed, Tag
from ..utils.feed_parsing import (
    FeedFileTooBigError,
    InvalidFeedFileError,
    MultipleFeedFoundError,
    NoFeedUrlFoundError,
    get_feed_metadata,
)


@require_http_methods(["GET", "POST"])
@alogin_required
async def subscribe_to_feed_view(request: AuthenticatedHttpRequest):
    tag_choices = await sync_to_async(Tag.objects.get_all_choices)(request.user)
    if request.method == HTTPMethod.GET:
        status = HTTPStatus.OK
        form = CreateFeedForm(tag_choices=tag_choices)
    else:
        status, form = await _handle_creation(request, tag_choices)

    return TemplateResponse(request, "feeds/create_feed.html", {"form": form}, status=status)


async def _handle_creation(request, tag_choices: list[tuple[str, str]]):  # noqa: PLR0911 Too many return statements
    form = CreateFeedForm(request.POST, tag_choices=tag_choices)
    if not form.is_valid():
        messages.error(request, _("Failed to create the feed"))
        return HTTPStatus.BAD_REQUEST, form

    try:
        async with httpx.AsyncClient(timeout=constants.HTTP_TIMEOUT) as client:
            feed_medata = await get_feed_metadata(form.feed_url, client=client)
        tags = await sync_to_async(Tag.objects.get_or_create_from_list)(
            request.user, form.cleaned_data["tags"]
        )
        feed = await sync_to_async(Feed.objects.create_from_metadata)(
            feed_medata, request.user, tags
        )
    except httpx.HTTPError:
        messages.error(
            request,
            _(
                "Failed to fetch the feed. Please check that the URL you entered is correct, that "
                "the feed exists and is accessible."
            ),
        )
        return HTTPStatus.NOT_ACCEPTABLE, form
    except IntegrityError:
        messages.error(request, _("You are already subscribed to this feed."))
        return HTTPStatus.CONFLICT, form
    except NoFeedUrlFoundError:
        messages.error(request, _("Failed to find a feed URL on the supplied page."))
        return HTTPStatus.BAD_REQUEST, form
    except MultipleFeedFoundError as e:
        form = CreateFeedForm(
            {
                "url": form.feed_url,
                "proposed_feed_choices": json.dumps(e.feed_urls),
            },
            tag_choices=tag_choices,
        )
        messages.warning(
            request, _("Multiple feeds were found at this location, please select the proper one.")
        )
        return HTTPStatus.BAD_REQUEST, form
    except FeedFileTooBigError:
        messages.error(
            request,
            _("The feed file is too big, we won't parse it. Try to find a more lightweight feed."),
        )
        return HTTPStatus.BAD_REQUEST, form
    except InvalidFeedFileError:
        messages.error(
            request,
            _(
                "We failed to parse the feed you supplied. Please check it is supported and "
                "matches the sync of a feed file."
            ),
        )
        return HTTPStatus.BAD_REQUEST, form
    else:
        # Empty form after success.
        form = CreateFeedForm(tag_choices=tag_choices)
        messages.success(request, _("Feed '%s' added") % feed.title)
        return HTTPStatus.CREATED, form
