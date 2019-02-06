"""Various ffprobe command line tools."""
import reel


class Devices(reel.Spool):
    """Provides information about system audio devices."""

    cmd = 'ffprobe'
    flags = ['-hide_banner', '-devices']

    def __init__(self):
        """."""
        super().__init__(self.cmd, xflags=self.flags)

    def list_outputs(self):
        """."""

    def list_inputs(self):
        """."""


class Codecs(reel.Spool):
    """Provides information about supported audio codecs."""

    cmd = 'ffprobe'
    flags = ['-hide_banner', '-codecs']

    def __init__(self):
        """."""
        super().__init__(self.cmd, xflags=self.flags)

    def audio_codecs(self):
        """."""
