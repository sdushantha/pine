import subprocess
import tempfile
import os
import numpy as np
import pytesseract
import cv2
import requests
import pyperclip
import rumps

"""
Features:
    All text extraction is done locally
    Saves text to clipboard
    Supports darkmode
    It does one thing, and it does it well
"""

__version__ = "2020.07.16"

# TODO: Need to figure out a way so that the user can select a language
#       and then we go and download it if that language data is not installed.
#       We might need to create a dictionary with language names and their
#       language codes.
#       https://tesseract-ocr.github.io/tessdoc/Data-Files.html
lang = "eng"
trained_data = f"{lang}.traineddata"
trained_data_path = "/usr/local/share/tessdata"


def get_trained_data(lang):
    """
    Download the trained data from tesseract's GitHub repo
    """
    try:
        r = requests.get(f"https://github.com/tesseract-ocr/tessdata_best/raw/master/{trained_data}")
        with open(f"{trained_data_path}/{trained_data}", "wb") as f:
            f.write(r.content)
        return True
    except requests.ConnectionError:
        return False


def is_darkmode() -> bool:
    """
    Check if the user is using dark mode
    """
    try:
        status = subprocess.check_output("defaults read -g AppleInterfaceStyle".split(), stderr=subprocess.STDOUT).decode()
    except subprocess.CalledProcessError:
        return False

    return True


def notify(title, text):
    """
    Send a notification

    title   --   title of notification
    text    --   description/summary of notification
    """
    # rumps.notification doesnt seems to work properly.
    # I should probably use subprocess instead, but I kept messing up the command because
    # of the many quatation marks it has. Will fix later, not high priority at the moment.
    os.system("""osascript -e 'display notification "{}" with title "{}"'""".format(text, title))


def take_screenshot() -> tuple:
    """
    Take a screenshot by selecting an area. This just uses
    macOS's default screencapture command
    """
    # Create a temporary file where we can store the screenshot
    # Source: https://stackoverflow.com/a/8577225/9215267
    _, file_path = tempfile.mkstemp()

    # From the man page:
    # -i         capture screen interactively, by selection or window
    # -s         only allow mouse selection mode
    # -x         do not play sounds
    subprocess.run(f"screencapture -i -s -x {file_path}".split())

    # We are checking if a screenshot was taken by checking if the
    # file is empty or not.
    # Source: https://stackoverflow.com/a/2507871/9215267
    if os.stat(file_path).st_size == 0:
        file_path = None
        return False, file_path

    return True, file_path


def is_dark(image) -> bool:
    """
    Check the image is mostley dark
    Source: https://stackoverflow.com/a/52506830/9215267

    image   --  the image data
    """
    threshold = 127
    return  np.mean(image) < threshold


class Pine(rumps.App):
    def __init__(self):

        # If the user is using dark mode, then the icons have to be
        # white so that they are visible.
        icon_color = "black"
        if is_darkmode():
            icon_color = "white"

        super(Pine, self).__init__(
            name="Pine",
            icon=f"icons/{icon_color}_logo.ico"
            )

        select_text = rumps.MenuItem("Select Text", icon=f"icons/{icon_color}_select.png")
        about = rumps.MenuItem("About")
        self.menu = [select_text, about]

    @rumps.clicked("Select Text", key="s")
    def runApp(self, _):
        image_captured, file_path = take_screenshot()
        if not image_captured:
            return

        if not os.path.isfile(f"{trained_data_path}/{trained_data}"):
            notify("Pine", f"Downloading language data for {lang}")
            if not get_trained_data(lang):
                notify("Pine", "Was not able to connect to internet")

        image = cv2.imread(file_path)

        if is_dark(image):
            # Since the image is dark, we need to invert it. This is because
            # tesseract is better at finding text on images with light
            # background and dark text
            # Source: https://stackoverflow.com/a/40954142/9215267
            image = cv2.bitwise_not(image)

        # From the man page:
        #  --psm NUM             Specify page segmentation mode.
        #  --oem NUM             Specify OCR Engine mode.
        # Source: https://www.pyimagesearch.com/2017/07/10/using-tesseract-ocr-python
        custom_config = "--oem 3 --psm 6"
        text = pytesseract.image_to_string(image, config=custom_config, lang=lang)

        if len(text) != 0:
            pyperclip.copy(text)
            notify("Pine", "Text Copied!")

    @rumps.clicked("About")
    def show_about(self, _):
        rumps.alert(title="Pine",
                    message=f"A simple image to text OCR scanner\nVersion {__version__}\nBy Siddharth Dushantha")

if __name__ == "__main__":
    Pine().run()
