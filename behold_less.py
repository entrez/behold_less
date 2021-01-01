###
# Copyright (c) 2020 by Michael Meyer <me@entrez.cc>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
###

try:
    import re
    import weechat
    import_ok = True
except ImportError:
    import_ok = False

SCRIPT_NAME = "behold_less"
SCRIPT_AUTHOR = "Michael Meyer <me@entrez.cc>"
SCRIPT_VERSION = "0.1.0"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Hide Beholder and Rodney spam"


# set min_turn or min_points to "" to disable showing events fitting that rule
# always_show_users: always show events from users in this comma-delimited list
# always_show_variants: always show events from variants in this list
# always_show_events: comma-delimited regexes that can match events
# buffer_name: set to "" in order to hide filtered messages entirely
options = {"min_turn": "20000",
           "min_points": "40000",
           "always_show_users": "",
           "always_show_variants": "",
           "always_show_events": "^ascended$,"
                                 "(wished for|made (his|her|their) "
                                 "first( artifact)? wish)",
           "buffer_name": "behold_less"}

# show debug messages
DEBUG = False

beholder_re = re.compile("\[[^\]]*\] \[(.*?[0-9])?(?P<variant>[A-Za-z]*[0-9]*)[^\]]*\] (?P<user>\S*) \((?P<class>\S*) (?P<race>\S*) (?P<gender>\S*) (?P<alignment>\S*)\)(?:, (?P<points>[0-9]*) points, T:(?P<endturn>[0-9]*), (?P<reason>.*)| (?P<event>.*?),? on T:(?P<eventturn>[0-9]*))")
rodney_re = re.compile("(?:\[(?P<variant>[^\]]*)\] )?(?P<user>\S*) \((?P<class>\S*) (?P<race>\S*) (?P<gender>\S*) (?P<alignment>\S*)\)(?:, (?P<points>[0-9]*) points, T:(?P<endturn>[0-9]*), (?P<reason>.*))")
comma_delimit = re.compile(r"(?<!\\),")


def get_option_list(opt):
    return [i.replace("\,", ",").strip() for i
            in comma_delimit.split(options.get(opt, "")) if i.strip() != ""]


def option_on(opt):
    return options.get(opt, "").strip() == "on"


def debug_print(msg, *args, **kwargs):
    if DEBUG:
        print(msg.format(*args), **kwargs)


def set_up_options():
    for option, default_value in options.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, default_value)
        else:
            options[option] = weechat.config_get_plugin(option)


def config_hook(data, option, value):
    _, option = option.rsplit(".", 1)
    options[option] = value
    return weechat.WEECHAT_RC_OK


def make_buffer_if_needed():
    if len(options["buffer_name"]) == 0:
        return ""
    buffer = weechat.buffer_search("", options["buffer_name"])
    if buffer is None or buffer == "":
        buffer = weechat.buffer_new(options["buffer_name"], "", "", "", "")
    return buffer


def hardfought_hook(data, line):
    msg = line.get("message", "")
    line_info = beholder_re.match(msg)
    # show unidentifiable messages (e.g. responses to commands like !lastgame)
    if line_info is None:
        debug_print("OK because no regex match: {}", msg)
        return weechat.WEECHAT_RC_OK
    user = line_info.group("user")
    vrnt = line_info.group("variant")
    # show message if user is in always_show_users list
    if user in get_option_list("always_show_users"):
        debug_print("OK because user {} allowed: {}", user, msg)
        return weechat.WEECHAT_RC_OK
    # show message if variant is in always_show_variants list
    if vrnt in get_option_list("always_show_variants"):
        debug_print("OK because variant {} allowed: {}", vrnt, msg)
        return weechat.WEECHAT_RC_OK
    if line_info.group("eventturn") is not None:
        turn = int(line_info.group("eventturn"))
        points = 0
        event = line_info.group("event")
    else:
        turn = int(line_info.groupdict().get("endturn", 0))
        points = int(line_info.groupdict().get("points", 0))
        event = line_info.group("reason")
    # show any match to regexes in always_show_events; by default this will
    # catch wishes and ascensions
    for show_regex in get_option_list("always_show_events"):
        if re.search(show_regex, event) is None:
            continue
        debug_print("OK because event (\"{}\") matched '{}' in "
                    "always_show_events: {}", event, show_regex, msg)
        return weechat.WEECHAT_RC_OK
    # show late-game events and deaths if configured to do so
    if options["min_turn"] != "" and turn >= int(options["min_turn"]):
        debug_print("OK because turn {} >= {}: {}",
                    turn, options["min_turn"], msg)
        return weechat.WEECHAT_RC_OK
    # likewise for high-point events and deaths
    if options["min_points"] != "" and points >= int(options["min_points"]):
        debug_print("OK because points {} >= {}: {}",
                    points, options["min_points"], msg)
        return weechat.WEECHAT_RC_OK
    return {"buffer": make_buffer_if_needed(), "notify_level": "-1"}


def nethack_hook(data, line):
    msg = line.get("message", "")
    line_info = rodney_re.match(msg)
    # show unidentifiable messages
    if line_info is None:
        debug_print("OK because no regex match: {}", msg)
        return weechat.WEECHAT_RC_OK
    # show message if user is in always_show_users list
    user = line_info.group("user")
    vrnt = line_info.group("variant")
    if user in get_option_list("always_show_users"):
        debug_print("OK because user {} allowed: {}", user, msg)
        return weechat.WEECHAT_RC_OK
    # show message if variant is in always_show_variants list
    if vrnt in get_option_list("always_show_variants"):
        debug_print("OK because variant {} allowed: {}", vrnt, msg)
        return weechat.WEECHAT_RC_OK
    turn = int(line_info.groupdict().get("endturn", 0))
    points = int(line_info.groupdict().get("points", 0))
    event = line_info.group("reason")
    # show any match to regexes in always_show_events
    for show_regex in get_option_list("always_show_events"):
        if re.search(show_regex, event) is None:
            continue
        debug_print("OK because event (\"{}\") matched '{}' in "
                    "always_show_events: {}", event, show_regex, msg)
        return weechat.WEECHAT_RC_OK
    # show late-game deaths
    if options["min_turn"] != "" and turn >= int(options["min_turn"]):
        debug_print("OK because turn {} >= {}: {}",
                    turn, options["min_turn"], msg)
        return weechat.WEECHAT_RC_OK
    # show high-point deaths
    if options["min_points"] != "" and points >= int(options["min_points"]):
        debug_print("OK because points {} >= {}: {}",
                    points, options["min_points"], msg)
        return weechat.WEECHAT_RC_OK
    return {"buffer": make_buffer_if_needed(), "notify_level": "-1"}


if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                         SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    set_up_options()
    weechat.hook_config("plugins.var.python.{}.*".format(SCRIPT_NAME),
                        "config_hook", "")
    hook = weechat.hook_line("", "*#hardfought", "nick_Beholder",
                             "hardfought_hook", "")
    hook = weechat.hook_line("", "*#NetHack", "nick_Rodney",
                             "nethack_hook", "")
