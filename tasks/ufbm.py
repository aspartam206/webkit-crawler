""" Unban Facebook Blocked Members """

import os
from itertools import chain

from core.application import get_settings_definition as application_settings
from core.reporter import get_settings_definition as reporter_settings
from core.helpers import evaluate_conditional, flatten_settings
from core.helpers import get_settings_value, is_active_settings

from modules.facebook import get_handlers as facebook_handlers
from modules.facebook import get_settings_definition as facebook_settings

ACTIVE_SETTINGS = (
    'application.',
    'reporter.',
    'facebook.home',
    'facebook.username',
    'facebook.password',
    'facebook.forum.name',
)

def _get_urls(app):
    fb_forum = app.settings['facebook.forum.name']
    fb_home_url = app.settings['facebook.home']

    urls = {
        'FORUM_BLOCKED_PATH': '/groups/' + fb_forum + '/blocked/',
        'FORUM_BLOCKED_URL': fb_home_url +'/groups/' + fb_forum + '/blocked/',
    }
    return urls


def do_unban_confirm(app):
    urls = _get_urls(app)

    js = """
    bot.trigger_wait_page_load = true;
    document.querySelector('button[name="remove_block"]').click();
    """
    app.execjs(js)

    app.set_expects([
        {
            'path': urls['FORUM_BLOCKED_PATH'] + '?', # regex
            'selectorExists': '#pagelet_group_blocked div[id^="member_"] .adminActions > a[ajaxify*="action=remove_block"]',
            'selectorNotExists': 'button[name="remove_block"]',
            'trigger': 'ufbm.doUnban',
        }])


def do_unban(app):
    urls = _get_urls(app)

    js = """
    var el = document.querySelector('#pagelet_group_blocked div[id^="member_"] .adminActions > a[ajaxify*="action=remove_block"]');
    bothelp_clickElement(el);
    """
    app.execjs(js)

    app.add_handler('ufbm.doUnbanConfirm', do_unban_confirm)

    app.set_expects([
        {
            'path': urls['FORUM_BLOCKED_PATH'] + '?', # regex
            'selectorExists': 'button[name="remove_block"]',
            'trigger': 'ufbm.doUnbanConfirm',
        }])


def unban(app):
    urls = _get_urls(app)

    app.clear_handlers()

    app.add_handler('ufbm.doUnban', do_unban)

    app.set_expects([
        {
            'path': urls['FORUM_BLOCKED_PATH'] + '?', # regex
            'selectorExists': '#pagelet_group_blocked div[id^="member_"] .adminActions > a[ajaxify*="action=remove_block"]',
            'trigger': 'ufbm.doUnban',
        }])


def unban_facebook_blocked_members(app):
    urls = _get_urls(app)

    for name, callback in facebook_handlers():
        app.add_handler(name, callback)

    app.add_handler('ufbm.unban', unban);

    app.add_queue(
        {
            'goto': app.settings['facebook.home'],
            'expects': [
            {
                'trigger': 'facebook.login',
                'triggerArgs':
                {
                    'username': app.settings['facebook.username'],
                    'password': app.settings['facebook.password'],
                }
            }],
        })

    app.add_queue(
        {
            'goto': urls['FORUM_BLOCKED_URL'],
            'expects': [
            {
                'trigger': 'ufbm.unban',
            }],
        })


def collect_settings(result, settings_in_file=None):
    primary_settings = dict(flatten_settings(settings_in_file or {}))

    all_settings = chain(facebook_settings(), application_settings(),
            reporter_settings())

    for name, config in all_settings:
        if 'default' in config:
            result[name] = config['default']

        if not is_active_settings(name, ACTIVE_SETTINGS):
            continue

        if not evaluate_conditional(config.get('if'), result):
            continue

        result[name] = get_settings_value(name, config, primary_settings)
