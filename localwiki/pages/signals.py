from django.db.models.signals import pre_save, post_save, pre_delete, m2m_changed
from django.utils.translation import ugettext as _
from django.conf import settings

from celery import shared_task
from actstream import action

from redirects.models import Redirect
from tags.models import PageTagSet
from maps.models import MapData

from .models import Page
from .cache import _page_cache_post_save, _page_cache_pre_delete, _pagetagset_m2m_changed


def _delete_page(sender, instance, raw, **kws):
    # Delete the source page if it exists.
    if Page.objects.filter(slug=instance.source, region=instance.region):
        p = Page.objects.get(slug=instance.source, region=instance.region)
        p.delete(comment=_("Redirect created"))


def _delete_redirect(sender, instance, raw, **kws):
    if Redirect.objects.filter(source=instance.slug, region=instance.region):
        r = Redirect.objects.get(source=instance.slug, region=instance.region)
        r.delete(comment=_("Page created"))


def _created_page_action(sender, instance, created, raw, **kws):
    """
    Notify this user's followers that the page was created (via activity stream).
    """
    if raw:
        return

    if not created:
        return

    if settings.IN_API_TEST:
        # XXX TODO Due to some horrible, difficult to figure out bug in
        # how force_authenticate() works in the API tests,
        # we have to skip signals here :/
        return

    user_edited = instance.versions.most_recent().version_info.user
    if not user_edited:
        return
    
    action.send(user_edited, verb='created page', action_object=instance)


@shared_task(ignore_result=True)
def _maybe_follow_region(page):
    from follow.models import Follow

    user_edited = page.versions.most_recent().version_info.user
    if not user_edited:
        return

    # User doesn't follow any regions yet.
    if not Follow.objects.filter(user=user_edited).exclude(target_region=None).exists():
        # Auto-follow this region
        Follow(user=user_edited, target_region=page.region).save()


def _post_save_maybe_follow(sender, instance, created, raw, **kws):
    """
    Follow this region after this page has been edited, in some cases.
    """
    if raw:
        return

    if settings.IN_API_TEST:
        # XXX TODO Due to some horrible, difficult to figure out bug in
        # how force_authenticate() works in the API tests,
        # we have to skip signals here :/
        return

    _maybe_follow_region.delay(instance)


# When a Redirect is created we want to delete the source Page if it
# exists.  This is so the redirect (which works via 404 fall-through)
# will be immediately functional.
pre_save.connect(_delete_page, sender=Redirect)

# When a page is created that overlaps with a Redirect we should
# delete the Redirect.
pre_save.connect(_delete_redirect, sender=Page)

if not settings.DISABLE_FOLLOW_SIGNALS:
    post_save.connect(_created_page_action, sender=Page)
    post_save.connect(_post_save_maybe_follow, sender=Page)

# Clear Page-related caches after a page, or a related object that's displayed
# inside the page, is modified.
# XXX TODO: on Django 1.6, experiment with their default
# autocommit mode. pre_delete() should work better in this case, on Django 1.6.
# As-is (Django 1.5), this can lead to a (albeit insignificant) cache consistency
# issue where a page is deleted, memcached does a delete (pre_delete()), and then
# a second request loads and caches the page in a separate thread before our
# thread commits.
post_save.connect(_page_cache_post_save, sender=Page)
pre_delete.connect(_page_cache_pre_delete, sender=Page)

post_save.connect(_page_cache_post_save, sender=PageTagSet)
pre_delete.connect(_page_cache_pre_delete, sender=PageTagSet)

m2m_changed.connect(_pagetagset_m2m_changed, sender=PageTagSet.tags.through)

post_save.connect(_page_cache_post_save, sender=MapData)
pre_delete.connect(_page_cache_pre_delete, sender=MapData)
