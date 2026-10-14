"""Does the dashboard work in a real browser? Builds both pages, opens one in headless Chrome, and prods it.

    python results/2026-10-12_robot_dashboard/check.py     (from the project root, about 1 minute)

Needs Google Chrome in /Applications; without it only the pages are built. A
copy of the page gets a short probe script appended (the page itself carries
no test code). The probe moves a pointer over the charts, presses keys,
clicks, switches robot and answer key, and writes what it saw into the page,
where this script reads it back. It also saves two pictures of the page.

Everything here is simulation with illustrative parameters.
"""

import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.getcwd())

from robot import config
from tools import dashboard

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

PROBE = r"""
<script>
(function () {
  var seen = {};
  function $(id) { return document.getElementById(id); }
  function tipText() { var t = $('tip'); return t.style.display === 'block' ? t.textContent : ''; }
  function point(node, type, fx, fy) {
    var box = node.getBoundingClientRect();
    node.dispatchEvent(new PointerEvent(type, { bubbles: true, clientX: box.left + box.width * fx, clientY: box.top + box.height * fy }));
  }
  function click(node, fx, fy) {
    var box = node.getBoundingClientRect();
    node.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: box.left + box.width * fx, clientY: box.top + box.height * fy }));
  }
  function pad(id) { var rects = $(id).querySelectorAll('svg > rect'); return rects[rects.length - 1]; }
  function key(id, name) { $(id).querySelector('svg').dispatchEvent(new KeyboardEvent('keydown', { key: name, bubbles: true })); }
  try {
    seen.ready = document.body.getAttribute('data-ready');
    seen.tiles = document.querySelectorAll('.tile').length;
    seen.lines_overview = $('chartAll').querySelectorAll('path.series').length;
    seen.start_day = $('dayOut').textContent;
    seen.due_at_start = document.querySelectorAll('.tile .status').length;

    point(pad('chartAll'), 'pointermove', 0.5, 0.5);
    seen.hover_overview = tipText();
    point(pad('chartAll'), 'pointerleave', 0.5, 0.5);
    seen.hover_gone = tipText();

    $('chartAll').querySelector('svg').dispatchEvent(new FocusEvent('focus'));
    seen.focus_overview = tipText().slice(0, 12);
    key('chartAll', 'ArrowRight');
    seen.after_arrow = tipText().slice(0, 12);

    click(pad('chartAll'), 0.25, 0.5);
    seen.day_after_click = $('dayOut').textContent;
    seen.due_after_click = document.querySelectorAll('.tile .status').length;

    document.querySelectorAll('.tile')[4].click();
    seen.title_after_tile = $('titleOne').textContent;
    seen.joint_select = $('joint').value;

    seen.lines_detail = $('chartOne').querySelectorAll('path.series').length;
    $('truth').click();
    seen.lines_detail_with_key = $('chartOne').querySelectorAll('path.series').length;
    seen.tile_with_key = document.querySelectorAll('.tile')[4].textContent.indexOf('Answer key') >= 0;

    var dots = $('chartSweep').querySelectorAll('circle.pt');
    seen.sweep_dots = dots.length;
    var box = dots[dots.length - 1].getBoundingClientRect(), sweepPad = pad('chartSweep');
    sweepPad.dispatchEvent(new PointerEvent('pointermove', { bubbles: true, clientX: box.left + box.width / 2 + 9, clientY: box.top + box.height / 2 + 9 }));
    seen.hover_sweep = tipText();

    $('run').value = '3';
    $('run').dispatchEvent(new Event('change', { bubbles: true }));
    seen.tiles_other_robot = document.querySelectorAll('.tile').length;

    $('day').value = '0';
    $('day').dispatchEvent(new Event('input', { bubbles: true }));
    seen.day_zero = $('dayOut').textContent;
    seen.first_tile_day_zero = document.querySelector('.tile .value').textContent;

    $('tableAll').open = true;
    seen.table_rows = $('tableAll').querySelectorAll('tr').length;
    seen.error = document.body.getAttribute('data-error');
  } catch (e) { seen.probe_failed = String(e); }
  var out = document.createElement('pre');
  out.id = 'probe';
  out.textContent = JSON.stringify(seen);
  document.body.append(out);
})();
</script>
"""


def chrome(args, expect=None):
    """Run headless Chrome with a throwaway profile. It sometimes does not exit after its work: stop it then."""
    with tempfile.TemporaryDirectory() as profile:
        command = [CHROME, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={profile}"] + args
        try:
            return subprocess.run(command, capture_output=True, text=True, timeout=60).stdout
        except subprocess.TimeoutExpired as stopped:
            if expect and os.path.exists(expect):
                return ""
            return stopped.stdout.decode() if stopped.stdout else ""


def main():
    pages = {}
    for scenario in sorted(config.RAMP_DAY):
        path = dashboard.write(os.path.join(config.SIMULATION_DIR, scenario), os.path.join(dashboard.OUT_DIR, f"dashboard_{scenario}.html"))
        data = dashboard.build_payload(os.path.join(config.SIMULATION_DIR, scenario))
        pages[scenario] = path
        print(f"{scenario}: {os.path.getsize(path) / 1e6:.1f} MB, {len(data['runs'])} robots of {data['runs'][0]['days']} days, "
              f"{len(data['runs'][0]['joints'])} joints, {len(data['runs'][0]['joints'][0]['sweeps'])} sweeps kept per joint")
        # the page flags a joint "service due" on the first day its index reaches the threshold: how late is that?
        late = [next(d for d, x in enumerate(j["index"]) if x is not None and x >= config.FAIL_W) - j["service_day"]
                for run in data["runs"] for j in run["joints"]]
        print(f"  'service due' is flagged {sum(late) / len(late):.1f} days after the true service day on average "
              f"({min(late)} to {max(late)} days, {len(late)} joints)")
    if not os.path.exists(CHROME):
        print("Google Chrome is not installed here: the pages were built, nothing was opened")
        return

    html = open(pages["ramp_early"], encoding="utf-8").read()
    with tempfile.TemporaryDirectory() as folder:
        probed = os.path.join(folder, "probed.html")
        with open(probed, "w", encoding="utf-8") as f:
            f.write(html.replace("</body>", PROBE + "</body>"))
        dom = chrome(["--virtual-time-budget=5000", "--window-size=1280,2000", "--dump-dom", f"file://{probed}?theme=light"])
    found = re.search(r'<pre id="probe">(.*?)</pre>', dom, re.S)
    if not found:
        print("the probe wrote nothing: the page did not finish loading")
        return
    seen = json.loads(found.group(1).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    print("\nwhat the probe saw in the early-ramp page (headless Chrome, 1280 px wide):")
    for name, value in seen.items():
        print(f"  {name:24s} {value!r}")

    for theme in ("light", "dark"):
        picture = os.path.join(dashboard.OUT_DIR, f"dashboard_ramp_early_{theme}.png")
        if os.path.exists(picture):
            os.remove(picture)
        chrome(["--window-size=1280,1500", "--hide-scrollbars", f"--screenshot={picture}",
                f"file://{pages['ramp_early']}?theme={theme}&joint=4&truth=1"], expect=picture)
        print(f"picture: {picture}  ({'written' if os.path.exists(picture) else 'NOT written'})")


if __name__ == "__main__":
    main()
