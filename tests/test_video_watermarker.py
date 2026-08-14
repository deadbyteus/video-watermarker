import os
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image, ImageFont

from video_watermarker import VideoWatermarker, clean_path, main


@pytest.fixture
def dirs(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    return str(input_dir), str(output_dir)


@pytest.fixture
def logo_file(tmp_path):
    path = tmp_path / "logo.png"
    Image.new("RGB", (40, 20), (255, 0, 0)).save(path)
    return str(path)


@pytest.fixture
def watermarker(dirs):
    input_dir, output_dir = dirs
    return VideoWatermarker(input_dir, output_dir)


class TestCleanPath:
    def test_strips_whitespace(self):
        assert clean_path("  /some/path  ") == "/some/path"

    def test_removes_newlines_and_carriage_returns(self):
        assert clean_path("/some\n/pa\rth\n") == "/some/path"

    def test_plain_path_unchanged(self):
        assert clean_path("/a/b/c") == "/a/b/c"


class TestInit:
    def test_creates_output_dir(self, dirs):
        input_dir, output_dir = dirs
        assert not os.path.exists(output_dir)
        wm = VideoWatermarker(input_dir, output_dir)
        assert os.path.isdir(output_dir)
        assert wm.output_dir == output_dir

    def test_defaults_output_dir_to_watermarked_subdir(self, dirs):
        input_dir, _ = dirs
        wm = VideoWatermarker(input_dir, "")
        expected = os.path.join(input_dir, "watermarked")
        assert wm.output_dir == expected
        assert os.path.isdir(expected)

    def test_cleans_paths(self, dirs):
        input_dir, output_dir = dirs
        wm = VideoWatermarker(f"  {input_dir}\n", f"{output_dir}\r\n")
        assert wm.input_dir == input_dir
        assert wm.output_dir == output_dir

    def test_no_logo_path(self, watermarker):
        assert watermarker.logo_path is None


class TestCreateWatermark:
    def test_from_logo_file(self, dirs, logo_file):
        input_dir, output_dir = dirs
        wm = VideoWatermarker(input_dir, output_dir, logo_file)
        assert isinstance(wm.watermark_img, np.ndarray)
        # RGBA conversion: height x width x 4 channels
        assert wm.watermark_img.shape == (20, 40, 4)

    def test_text_watermark_when_no_logo(self, watermarker):
        assert isinstance(watermarker.watermark_img, np.ndarray)
        assert watermarker.watermark_img.shape == (50, 150, 4)
        # Text pixels drawn onto the fully transparent canvas
        assert watermarker.watermark_img[:, :, 3].max() > 0

    def test_returns_none_on_invalid_logo(self, dirs):
        input_dir, output_dir = dirs
        wm = VideoWatermarker(input_dir, output_dir, "/nonexistent/logo.png")
        assert wm.watermark_img is None


class TestGetDefaultFont:
    def test_returns_usable_font(self, watermarker):
        font = watermarker._get_default_font(24)
        assert isinstance(font, (ImageFont.FreeTypeFont, ImageFont.ImageFont))

    def test_falls_back_when_no_font_found(self, watermarker):
        real_exists = os.path.exists
        with patch(
            "video_watermarker.os.path.exists",
            side_effect=lambda p: False if str(p).endswith((".ttf", ".ttc")) else real_exists(p),
        ), patch("video_watermarker.ImageFont.load_default") as load_default:
            font = watermarker._get_default_font(24)
        assert font is load_default.return_value

    def test_falls_back_on_error(self, watermarker):
        with patch(
            "video_watermarker.ImageFont.truetype", side_effect=OSError("boom")
        ), patch("video_watermarker.ImageFont.load_default") as load_default:
            font = watermarker._get_default_font(24)
        assert font is load_default.return_value


class TestCalculatePosition:
    VIDEO = (1920, 1080)
    MARK = (200, 100)

    def test_top_left(self, watermarker):
        assert watermarker.calculate_position(self.VIDEO, self.MARK, "top-left") == (10, 10)

    def test_top_right(self, watermarker):
        assert watermarker.calculate_position(self.VIDEO, self.MARK, "top-right") == (1710, 10)

    def test_bottom_left(self, watermarker):
        assert watermarker.calculate_position(self.VIDEO, self.MARK, "bottom-left") == (10, 970)

    def test_bottom_right(self, watermarker):
        assert watermarker.calculate_position(self.VIDEO, self.MARK, "bottom-right") == (1710, 970)

    def test_center(self, watermarker):
        assert watermarker.calculate_position(self.VIDEO, self.MARK, "center") == (860, 490)

    def test_unknown_position_defaults_to_top_right(self, watermarker):
        assert watermarker.calculate_position(self.VIDEO, self.MARK, "bogus") == (1710, 10)

    def test_custom_padding(self, watermarker):
        assert watermarker.calculate_position(self.VIDEO, self.MARK, "top-left", padding=25) == (25, 25)


def _mock_video(width=1920, height=1080, fps=30, duration=10.0):
    video = MagicMock()
    video.size = (width, height)
    video.w = width
    video.h = height
    video.fps = fps
    video.duration = duration
    return video


@pytest.fixture
def moviepy_mocks():
    with patch("video_watermarker.VideoFileClip") as video_clip, patch(
        "video_watermarker.ImageClip"
    ) as image_clip, patch(
        "video_watermarker.CompositeVideoClip"
    ) as composite_clip:
        video_clip.return_value = _mock_video()
        yield video_clip, image_clip, composite_clip


def _opacity_call(image_clip):
    chain = (
        image_clip.return_value.with_duration.return_value
        .with_fps.return_value.with_position.return_value
    )
    return chain.with_opacity.call_args[0][0]


class TestProcessVideo:
    def test_success_returns_output_path(self, watermarker, moviepy_mocks):
        _, _, composite_clip = moviepy_mocks
        result = watermarker.process_video("clip.mp4")
        expected = os.path.join(watermarker.output_dir, "clip.mp4")
        assert result == expected
        final = composite_clip.return_value.with_fps.return_value
        final.write_videofile.assert_called_once()
        assert final.write_videofile.call_args[0][0] == expected

    def test_fractional_transparency(self, watermarker, moviepy_mocks):
        _, image_clip, _ = moviepy_mocks
        watermarker.process_video("clip.mp4", transparency=0.3)
        assert _opacity_call(image_clip) == pytest.approx(0.7)

    def test_255_scale_transparency(self, watermarker, moviepy_mocks):
        _, image_clip, _ = moviepy_mocks
        watermarker.process_video("clip.mp4", transparency=51)
        assert _opacity_call(image_clip) == pytest.approx(0.8)

    def test_transparency_clamped_to_zero(self, watermarker, moviepy_mocks):
        _, image_clip, _ = moviepy_mocks
        watermarker.process_video("clip.mp4", transparency=300)
        assert _opacity_call(image_clip) == 0

    def test_watermark_scaled_to_video_width(self, watermarker, moviepy_mocks):
        _, image_clip, _ = moviepy_mocks
        watermarker.process_video("clip.mp4", scale=0.1)
        watermark_array = image_clip.call_args[0][0]
        # Video width 1920 * 0.1 = 192; text watermark is 150x50 -> height 64
        assert watermark_array.shape == (64, 192, 4)

    def test_closes_resources(self, watermarker, moviepy_mocks):
        video_clip, image_clip, composite_clip = moviepy_mocks
        watermarker.process_video("clip.mp4")
        video_clip.return_value.close.assert_called_once()
        composite_clip.return_value.with_fps.return_value.close.assert_called_once()

    def test_returns_none_on_error(self, watermarker):
        with patch(
            "video_watermarker.VideoFileClip", side_effect=OSError("cannot open")
        ):
            assert watermarker.process_video("clip.mp4") is None


class TestProcessDirectory:
    def _touch(self, directory, *names):
        for name in names:
            open(os.path.join(directory, name), "w").close()

    def test_counts_successes_and_failures(self, watermarker):
        self._touch(watermarker.input_dir, "a.mp4", "b.avi", "c.mov")
        with patch.object(
            watermarker, "process_video", side_effect=["/out/a.mp4", None, "/out/c.mov"]
        ) as process_video:
            successful, failed = watermarker.process_directory()
        assert (successful, failed) == (2, 1)
        assert process_video.call_count == 3

    def test_skips_unsupported_files(self, watermarker):
        self._touch(watermarker.input_dir, "notes.txt", "image.png", "video.mp4")
        with patch.object(
            watermarker, "process_video", return_value="/out/video.mp4"
        ) as process_video:
            successful, failed = watermarker.process_directory()
        assert (successful, failed) == (1, 0)
        process_video.assert_called_once_with("video.mp4", 0.1, "top-right", 0.5)

    def test_supported_extensions_case_insensitive(self, watermarker):
        self._touch(watermarker.input_dir, "UPPER.MP4", "clip.WebM")
        with patch.object(
            watermarker, "process_video", return_value="/out/x"
        ) as process_video:
            successful, failed = watermarker.process_directory()
        assert (successful, failed) == (2, 0)
        assert process_video.call_count == 2

    def test_empty_directory(self, watermarker):
        assert watermarker.process_directory() == (0, 0)


class TestMain:
    def test_parses_args_and_processes(self, dirs):
        input_dir, output_dir = dirs
        argv = [
            "video_watermarker.py",
            "--input-dir", input_dir,
            "--output-dir", output_dir,
            "--scale", "0.2",
            "--position", "center",
            "--transparency", "0.3",
        ]
        with patch("video_watermarker.VideoWatermarker") as watermarker_cls, patch(
            "sys.argv", argv
        ):
            watermarker_cls.return_value.process_directory.return_value = (1, 0)
            main()
        watermarker_cls.assert_called_once_with(input_dir, output_dir, None)
        watermarker_cls.return_value.process_directory.assert_called_once_with(
            0.2, "center", 0.3
        )

    def test_requires_input_dir(self):
        with patch("sys.argv", ["video_watermarker.py"]):
            with pytest.raises(SystemExit):
                main()

    def test_rejects_invalid_position(self, dirs):
        input_dir, _ = dirs
        argv = [
            "video_watermarker.py",
            "--input-dir", input_dir,
            "--position", "middle",
        ]
        with patch("sys.argv", argv):
            with pytest.raises(SystemExit):
                main()
