import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))

import build  # noqa: E402

FRAGMENT = """
<section id="s1"><h2>한눈에 <b>보기</b></h2>
  <article class="topic" id="t-why"><h3>왜 필요할까?</h3>
    <div class="layer eli5"><span class="layer-title">쉽게 말하면</span><p class="lead">비유.</p></div>
    <div class="sum" hidden><p class="sum-lead">핵심.</p></div>
  </article>
</section>
<section id="s2"><h2>더 보기</h2>
  <article class="topic" id="t-how"><h3>어떻게?</h3>
    <div class="layer eli5"><span class="layer-title">쉽게 말하면</span><p class="lead">$a+b$</p></div>
  </article>
  <script>console.log('w')</script>
</section>
"""


class BuildTest(unittest.TestCase):
    def test_fills_every_placeholder(self):
        out = build.build("DNS & 주소", "전화번호부", "dns", FRAGMENT)
        self.assertNotRegex(out, r"\{\{[A-Z_]+\}\}")
        self.assertIn("<title>ELI5: DNS &amp; 주소</title>", out)
        self.assertIn('data-range="eli5-dns"', out)
        self.assertIn('data-panels="note"', out)

    def test_toc_from_sections(self):
        out = build.build("T", "S", "t", FRAGMENT)
        self.assertIn('<a href="#s1">한눈에 보기</a><a href="#s2">더 보기</a>', out)

    def test_scripts_moved_before_body_end(self):
        out = build.build("T", "S", "t", FRAGMENT)
        main = out[out.index("<main>"):out.index("</main>")]
        self.assertNotIn("console.log('w')", main)
        self.assertLess(out.index("console.log('w')"), out.index('<script id="theme-ui">'))

    def test_template_is_verbatim_note_template(self):
        tpl = (SKILL / "assets" / "note-template.html").read_text(encoding="utf-8")
        self.assertIn("function setupNote()", tpl)
        self.assertEqual(sorted(set(re.findall(r"\{\{([A-Z_]+)\}\}", tpl))),
                         sorted(["BRAND", "DESCRIPTION", "FOOTER", "PAGE_TITLE", "RANGE",
                                 "SCRIPTS", "SECTIONS", "SUBTITLE", "TITLE", "TOC"]))

    def test_rejects_bad_input(self):
        cases = {
            "no section": "<p>x</p>",
            "no topic": '<section id="s1"><h2>a</h2></section>',
            "dup id": FRAGMENT.replace('id="t-how"', 'id="t-why"'),
            "reserved id": FRAGMENT.replace('id="t-how"', 'id="pager-next"'),
            "leftover": FRAGMENT.replace("비유.", "{{TITLE}}"),
        }
        for name, frag in cases.items():
            with self.subTest(name), self.assertRaises(build.BuildError):
                build.build("T", "S", "t", frag)
        with self.assertRaises(build.BuildError):
            build.build("T", "S", "Bad Slug", FRAGMENT)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            src, out = Path(d, "body.html"), Path(d, "out", "x.html")
            src.write_text(FRAGMENT, encoding="utf-8")
            ok = subprocess.run([sys.executable, str(SKILL / "scripts" / "build.py"), "--title", "T",
                                 "--subtitle", "S", "--slug", "t", "--sections", str(src), "--out", str(out)],
                                capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertTrue(out.exists())
            src.write_text("<p>x</p>", encoding="utf-8")
            bad = subprocess.run([sys.executable, str(SKILL / "scripts" / "build.py"), "--title", "T",
                                  "--subtitle", "S", "--slug", "t", "--sections", str(src), "--out", str(out)],
                                 capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(bad.returncode, 1)
            self.assertIn("FAIL", bad.stderr)


if __name__ == "__main__":
    unittest.main()
