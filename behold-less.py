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

SCRIPT_NAME = "behold-less"
SCRIPT_AUTHOR = "Michael Meyer <me@entrez.cc>"
SCRIPT_VERSION = "0.0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Hide Beholder and Rodney spam"

# set MIN_TURN or MIN_POINTS to a negative number to disable that rule
# (i.e. set MIN_TURN = -1, MIN_POINTS = 2000 to show events with at least 2000
# points and ignore turn count)
# of whether they
MIN_TURN = 15000
MIN_POINTS = 20000
# events from users in this list will never be hidden
ALWAYS_SHOW_USERS = ["qt"]
# set BUFFER_NAME to "" in order to hide filtered messages entirely
BUFFER_NAME = "behold-less"

beholder_re = re.compile("\[[^\]]*\] \[.*[0-9](?P<variant>[A-Za-z]*)[^\]]*\] (?P<user>\S*) \((?P<class>\S*) (?P<race>\S*) (?P<gender>\S*) (?P<alignment>\S*)\)(?:, (?P<points>[0-9]*) points, T:(?P<endturn>[0-9]*), (?P<reason>.*)| (?P<event>.*), on T:(?P<eventturn>[0-9]*))")
rodney_re = re.compile("(?P<user>\S*) \((?P<class>\S*) (?P<race>\S*) (?P<gender>\S*) (?P<alignment>\S*)\)(?:, (?P<points>[0-9]*) points, T:(?P<endturn>[0-9]*), (?P<reason>.*))")
wish_re = re.compile("(?:wished for|made (?:his|her|their) first(?: artifact)? wish -) \"(?P<wish>.*)\"")
ascension_re = re.compile("ascended")


def make_buffer_if_needed():
    if len(BUFFER_NAME) == 0:
        return ""
    buffer = weechat.buffer_search("", BUFFER_NAME)
    if buffer is None or buffer == "":
        buffer = weechat.buffer_new(BUFFER_NAME, "", "", "", "")
    return buffer


def hardfought_hook(data, line):
    msg = line.get("message", "")
    line_info = beholder_re.match(msg)
    # show unidentifiable messages by default
    if line_info is None:
        return
    user = line_info.group("user")
    if user in ALWAYS_SHOW_USERS:
        return
    if line_info.group("eventturn") is not None:
        turn = int(line_info.group("eventturn"))
        points = 0
        event = line_info.group("event")
        # if the event involves wishing, show it regardless of turn count
        if wish_re.match(event):
            return
    else:
        turn = int(line_info.groupdict().get("endturn", 0))
        points = int(line_info.groupdict().get("points", 0))
        event = line_info.group("reason")
        # show all ascensions
        if ascension_re.search(event):
            return
    # show late-game or high-point events and deaths
    if (MIN_TURN >= 0 and turn >= MIN_TURN) \
            or (MIN_POINTS >= 0 and points >= MIN_POINTS):
        return
    return {"buffer": make_buffer_if_needed(), "notify_level": "-1"}


def nethack_hook(data, line):
    msg = line.get("message", "")
    line_info = rodney_re.match(msg)
    # show unidentifiable messages by default
    if line_info is None:
        return
    user = line_info.group("user")
    if user in ALWAYS_SHOW_USERS:
        return
    turn = int(line_info.groupdict().get("endturn", 0))
    points = int(line_info.groupdict().get("points", 0))
    event = line_info.group("reason")
    # show all ascensions
    if ascension_re.search(event):
        return
    # show late-game deaths
    if (MIN_TURN >= 0 and turn >= MIN_TURN) \
            or (MIN_POINTS >= 0 and points >= MIN_POINTS):
        return
    return {"buffer": make_buffer_if_needed(), "notify_level": "-1"}


if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                         SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    hook = weechat.hook_line("", "*#hardfought", "nick_Beholder",
                             "hardfought_hook", "")
    hook = weechat.hook_line("", "*#NetHack", "nick_Rodney",
                             "nethack_hook", "")
