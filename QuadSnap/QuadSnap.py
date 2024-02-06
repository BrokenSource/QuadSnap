from . import *


@define
class QuadSnap(BrokenApp):
    OUTPUT = QUADSNAP.DIRECTORIES.PACKAGE/"Snap" if BROKEN_RELEASE else QUADSNAP.DIRECTORIES.DATA

    @staticmethod
    def snap(
        image: Option[Image, URL, Path],
        *,
        grid_size: int=2,
        echo: bool=False
    ) -> Iterable[Image]:
        """Split an image or directory into a NxN grid generator"""

        # If it's a directory, snap every image on it
        if isinstance(image, (str, Path)) and Path(image).is_dir():
            for path in Path(image).rglob(r"*.{jpg,jpeg,png,bmp}"):
                yield from QuadSnap.snap(image=path)
            return

        # Load image and calculate block resolutions
        image = BrokenUtils.load_image(image, echo=echo)
        w, h = image.size[0]//grid_size, image.size[1]//grid_size

        # Crop and yield each block: top to bottom, left to right
        for block in [
            image.crop((y*w, x*h, (y+1)*w, (x+1)*h))
            for x in range(grid_size)
            for y in range(grid_size)
        ]:
            yield block

    def cli_snap(self, thing: Option[Image, URL, Path]):
        """Snap and save to a Filename or URL Stem"""
        if (image := BrokenUtils.load_image(thing, echo=False)):
            print()
            log.success(f"Snapping Image {thing}")
            for i, block in enumerate(QuadSnap.snap(image)):
                output = self.OUTPUT/f"{Path(thing).stem}-{i+1}.jpg"
                log.info(f"Saving {output}")
                block.save(output, quality=95)

    @staticmethod
    def get_clipboard() -> str:
        return pyperclip.paste()

    @staticmethod
    def watchdog_clipboard(previous: str="") -> Iterable[str]:
        while True:
            if (current := QuadSnap.get_clipboard()) != previous:
                previous = current
                yield current
            time.sleep(0.1)

    @staticmethod
    def watchdog_stdin() -> Iterable[str]:
        while True:
            yield input(":: Enter a URL or Drag and Drop a File or Directory: ")

    def snap_stdin(self):
        """Infinitely snap images from the stdin"""
        for snap in self.watchdog_stdin():
            self.cli_snap(snap)

    def snap_clipboard(self):
        """Infinitely snap images from the clipboard"""
        for snap in self.watchdog_clipboard():
            self.cli_snap(snap)

    def cli(self) -> None:

        # Snap from argv inputs (direct script usage)
        if len(sys.argv) > 1:
            log.info("Snapping argv inputs")
            for arg in sys.argv[1:]:
                self.cli_snap(arg)
            return

        # Information about basic usage
        log.success("Watching clipboard for new images - File, Directory or URL")
        log.warning("• You can also drag and drop files here and press Enter to snap them")
        log.warning("• Directories are recursively snapped")
        log.info(f"Will save resulting images on ({self.OUTPUT})")

        # Start threads for clipboard and stdin
        Thread(target=self.snap_clipboard, daemon=True).start()
        Thread(target=self.snap_stdin,     daemon=True).start()

        # The threads do the work :)
        while True:
            time.sleep(1)
