from NanoVNASaver.Hardware.LiteVNA64 import ScreenshotData

VALID_HEADER = b"\xe0\x01@\x01\x10"


class TestScreenshotData:

    @staticmethod
    def test_from_header() -> None:
        result = ScreenshotData.from_header(VALID_HEADER)

        assert result.width == 480
        assert result.height == 320
        assert result.pixel_size == 16
        assert len(result.data) == 0

    @staticmethod
    def test_data_size() -> None:
        assert ScreenshotData(0, 0, 0).data_size() == 0
        assert ScreenshotData(480, 320, 16).data_size() == 307200

    @staticmethod
    def test_repr() -> None:
        assert f"{ScreenshotData(0,0,0)}" == "0x0 0bits (0 Bytes)"
        assert (
            f"{ScreenshotData(480,320,16)}" == "480x320 16bits (307200 Bytes)"
        )

    @staticmethod
    def test_rgb565_to_888() -> None:
        assert ScreenshotData.rgb565_to_888(0x0000) == (0x00, 0x00, 0x00)
        assert ScreenshotData.rgb565_to_888(0xFFE0) == (0xFF, 0xFF, 0x00)
        assert ScreenshotData.rgb565_to_888(0xFFFF) == (0xFF, 0xFF, 0xFF)

    @staticmethod
    def test_get_rgb888_data() -> None:
        img = ScreenshotData(0, 0, 0)
        img.data = b"\x00\x00\xff\xe0\xff\xff"

        result = img.get_rgb888_data()

        assert len(result) == 3 * 3
        assert result == b"\x00\x00\x00\xFF\xFF\x00\xFF\xFF\xFF"
