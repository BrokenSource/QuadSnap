from QuadSnap import *

def get_clipboard() -> str:
    """Get clipboard contents"""
    try:
        if BrokenPlatform.Linux:
            return shell(get_binary_cached("xclip"), "-selection", "clipboard", "-o", echo=False, output=True).strip()
        elif BrokenPlatform.Windows:
            # FIXME: Get -Format FileDropList and maybe -Format Image to work, might need to unset them afterwards
            return shell(get_binary_cached("powershell"), "Get-Clipboard", echo=False, output=True).strip()
        elif BrokenPlatform.MacOS:
            return shell(get_binary_cached("pbpaste"), "r", echo=False, output=True).strip()
        else:
            error(f"Unknown Platform [{BrokenPlatform.Name}] to get clipboard")
            return None
    except UnicodeDecodeError:
        return None
    except Exception as e:
        raise e

class QuadSnap:
    FIRST_TIME = True

    def __init__(self) -> None:
        self.OUTPUT_DIRECTORY = QUADSNAP_DIRECTORIES.DATA

        # Images can be drag and dropped to the binary, snap them
        if len(argv) > 1:
            info("Snapping argv inputs to current directory")

            # Change output directory relative to executable
            self.OUTPUT_DIRECTORY = QUADSNAP_DIRECTORIES.EXECUTABLE/"QuadSnapped"
            mkdir(self.OUTPUT_DIRECTORY)

            # Snap argv inputs
            for arg in argv[1:]:
                self.snap(this=arg)
            return

        # Start threads for clipboard and stdin
        Thread(target=self.watchdog_clipboard, daemon=True).start()
        Thread(target=self.watchdog_stdin,     daemon=True).start()

        # Main thread to wait infinitely
        while True: sleep(1)

    # # Watchdog functions

    def watchdog_stdin(self) -> None:
        success("Watching clipboard for new images - File, Directory or URL")
        warning("• You can also drag and drop files here and press Enter to snap them")
        warning("• Directories are recursively snapped")
        warning("• Input nothing to exit or close this window")
        info(f"Will save resulting images on [{self.OUTPUT_DIRECTORY}]")
        while True:
            if (snap := input("")) == "":
                system.exit(1)
            self.snap(this=snap)

    def watchdog_clipboard(self) -> None:
        """Snap every new clipboard updated contents thread"""
        old_clipboard = get_clipboard()
        while True:
            self.clipboard = get_clipboard()
            if self.clipboard != old_clipboard:
                info(f"Clipboard updated to [{self.clipboard}]")
                old_clipboard = self.clipboard
                self.snap(this=self.clipboard)
            sleep(0.1)

    # # Core logic of QuadSnap

    def snap(self, this: Tuple[Path, URL], recursive: bool=True) -> List[PilImage]:
        """Snap an Midjourney image from a path or url into 4 quadrants"""

        # If it's a directory, snap everything on it
        if Path(this).is_dir():
            for path in Path(this).rglob("*"):
                self.snap(this=path, recursive=recursive)
            return

        # Attempt loading the image from path, url
        image = BrokenSmart.load_image(this, echo=False)

        # Return if input isn't an image
        if image is None:
            return

        # # Success, image is something

        success(f"Snapping image [{this}]")

        # Break the image into 4 quadrants
        # Without using BrokenImageUtils
        w, h = image.size[0]//2, image.size[1]//2

        # Crop image into the quadrants
        quadrants = [
            image.crop((0, 0,   w, h  )),
            image.crop((w, 0, w*2, h  )),
            image.crop((0, h,   w, h*2)),
            image.crop((w, h, w*2, h*2))
        ]

        # # Save the quadrants
        for i, quadrant in enumerate(quadrants):
            output = self.OUTPUT_DIRECTORY/f"{Path(this).stem}_{i}.jpg"
            info(f"Saving [Quadrant {i}] to [{output}]")
            quadrant.save(output, quality=100)

        # Open output directory on first snap
        if QuadSnap.FIRST_TIME:
            open_in_file_explorer(self.OUTPUT_DIRECTORY)
            QuadSnap.FIRST_TIME = False