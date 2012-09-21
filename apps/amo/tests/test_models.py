
from mock import Mock
from nose.tools import eq_

import amo.models
from amo.models import manual_order
from amo.tests import TestCase
from amo import models as context
from addons.models import Addon

from gelato.models import base

class ManualOrderTest(TestCase):
    fixtures = ('base/apps', 'base/addon_3615', 'base/addon_5299_gcal',
                'base/addon_40')

    def test_ordering(self):
        """Given a specific set of primary keys, assure that we return addons
        in that order."""

        semi_arbitrary_order = [40, 5299, 3615]
        addons = manual_order(Addon.objects.all(), semi_arbitrary_order)
        eq_(semi_arbitrary_order, [addon.id for addon in addons])


def test_skip_cache():
    eq_(getattr(base._locals, 'skip_cache', False), False)
    with base.skip_cache():
        eq_(base._locals.skip_cache, True)
        with base.skip_cache():
            eq_(base._locals.skip_cache, True)
        eq_(base._locals.skip_cache, True)
    eq_(base._locals.skip_cache, False)


def test_use_master():
    local = context.multidb.pinning._locals
    eq_(getattr(local, 'pinned', False), False)
    with context.use_master():
        eq_(local.pinned, True)
        with context.use_master():
            eq_(local.pinned, True)
        eq_(local.pinned, True)
    eq_(local.pinned, False)


class TestModelBase(TestCase):
    fixtures = ['base/addon_3615']

    def setUp(self):
        self.saved_cb = base._on_change_callbacks.copy()
        base._on_change_callbacks.clear()
        self.cb = Mock()
        Addon.on_change(self.cb)

    def tearDown(self):
        amo.models._on_change_callbacks = self.saved_cb

    def test_change_called_on_new_instance_save(self):
        for create_addon in (Addon, Addon.objects.create):
            addon = create_addon(site_specific=False, type=amo.ADDON_EXTENSION)
            addon.site_specific = True
            addon.save()
            assert self.cb.called
            kw = self.cb.call_args[1]
            eq_(kw['old_attr']['site_specific'], False)
            eq_(kw['new_attr']['site_specific'], True)
            eq_(kw['instance'].id, addon.id)
            eq_(kw['sender'], Addon)

    def test_change_called_on_update(self):
        addon = Addon.objects.get(pk=3615)
        addon.update(site_specific=False)
        assert self.cb.called
        kw = self.cb.call_args[1]
        eq_(kw['old_attr']['site_specific'], True)
        eq_(kw['new_attr']['site_specific'], False)
        eq_(kw['instance'].id, addon.id)
        eq_(kw['sender'], Addon)

    def test_change_called_on_save(self):
        addon = Addon.objects.get(pk=3615)
        addon.site_specific = False
        addon.save()
        assert self.cb.called
        kw = self.cb.call_args[1]
        eq_(kw['old_attr']['site_specific'], True)
        eq_(kw['new_attr']['site_specific'], False)
        eq_(kw['instance'].id, addon.id)
        eq_(kw['sender'], Addon)

    def test_change_is_not_recursive(self):

        class fn:
            called = False

        def callback(old_attr=None, new_attr=None, instance=None,
                     sender=None, **kw):
            fn.called = True
            # Both save and update should be protected:
            instance.update(site_specific=False)
            instance.save()

        Addon.on_change(callback)

        addon = Addon.objects.get(pk=3615)
        addon.save()
        assert fn.called
        # No exception = pass

    def test_safer_get_or_create(self):
        data = {'guid': '123', 'type': amo.ADDON_EXTENSION}
        a, c = Addon.objects.safer_get_or_create(**data)
        assert c
        b, c = Addon.objects.safer_get_or_create(**data)
        assert not c
        eq_(a, b)
