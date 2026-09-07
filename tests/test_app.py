import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app


class TestShortcutsJson(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(
            (Path(app.__file__).parent / "shortcuts.json").read_text(encoding="utf-8"))

    def test_default_section_exists(self):
        self.assertIn("_default", self.data)

    def test_entries_well_formed(self):
        for section_key, section in self.data.items():
            self.assertIn("shortcuts", section, section_key)
            for item in section["shortcuts"]:
                self.assertTrue(item["key"].strip(), f"{section_key}: key vazio")
                self.assertTrue(item["desc"].strip(), f"{section_key}: desc vazio")


class TestSplitKey(unittest.TestCase):
    def test_simple_combo(self):
        self.assertEqual(app.split_key("Ctrl+C"), [["Ctrl", "C"]])

    def test_plain_key(self):
        self.assertEqual(app.split_key("Page Up"), [["Page Up"]])

    def test_leader_sequence(self):
        self.assertEqual(app.split_key("Ctrl+X → N"), [["Ctrl", "X"], ["N"]])

    def test_bare_arrow(self):
        self.assertEqual(app.split_key("→"), [["→"]])


class TestClampPosition(unittest.TestCase):
    RECT = app.Rect(100, 50, 1920, 1080)

    def test_inside_unchanged(self):
        self.assertEqual(app.clamp_position(150, 100, 380, 340, self.RECT), (150, 100))

    def test_clamps_right_bottom(self):
        self.assertEqual(app.clamp_position(1900, 1050, 380, 340, self.RECT), (1540, 740))

    def test_clamps_left_top(self):
        self.assertEqual(app.clamp_position(0, 0, 380, 340, self.RECT), (100, 50))


class TestPlatformSmoke(unittest.TestCase):
    def test_process_map_shape(self):
        pmap = app._get_process_map()
        self.assertTrue(pmap)
        for pid, (name, ppid) in list(pmap.items())[:5]:
            self.assertIsInstance(pid, int)
            self.assertIsInstance(name, str)
            self.assertIsInstance(ppid, int)

    def test_foreground_returns_str(self):
        self.assertIsInstance(app.get_foreground_exe(), str)

    def test_monitors_shape(self):
        for mon in app.get_all_monitors():
            self.assertEqual(set(mon), {"left", "top", "width", "height"})
            self.assertGreater(mon["width"], 0)
            self.assertGreater(mon["height"], 0)

    def test_work_rect_attrs(self):
        rect = app.get_monitor_work_rect(0, 0)
        if rect is not None:
            for attr in ("left", "top", "right", "bottom"):
                self.assertTrue(hasattr(rect, attr))


if __name__ == "__main__":
    unittest.main()
