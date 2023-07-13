from QuadSnap import *

get_binary_cached = lru_cache()(BrokenPath.get_binary)

def get_clipboard() -> str:
    """Get clipboard contents"""
    try:
        if BrokenPlatform.OnLinux:
            return shell(get_binary_cached("xclip"), "-selection", "clipboard", "-o", echo=False, output=True).strip()
        elif BrokenPlatform.OnWindows:
            # FIXME: Get -Format FileDropList and maybe -Format Image to work, might need to unset them afterwards
            return shell(get_binary_cached("powershell"), "Get-Clipboard", echo=False, output=True).strip()
        elif BrokenPlatform.OnMacOS:
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
            BrokenPath.mkdir(self.OUTPUT_DIRECTORY)

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

    def snap(self, this: Tuple[Path, URL], recursive: bool=True, grid_size=2) -> List[PilImage]:
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
        w, h = image.size[0]//grid_size, image.size[1]//grid_size

        # Crop image into the quadrants based on grid_size
        quadrants = [
            image.crop((j*w, i*h, (j+1)*w, (i+1)*h))
            for i in range(grid_size)
            for j in range(grid_size)
        ]

        # # Save the quadrants
        for i, quadrant in enumerate(quadrants):
            output = self.OUTPUT_DIRECTORY/f"{Path(this).stem}-{i+1}.jpg"
            info(f"Saving [Quadrant {i}] to [{output}]")
            quadrant.save(output, quality=100)

        # Open output directory on first snap
        if QuadSnap.FIRST_TIME:
            BrokenPath.open_in_file_explorer(self.OUTPUT_DIRECTORY)
            QuadSnap.FIRST_TIME = False
