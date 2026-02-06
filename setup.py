from setuptools import setup

APP = ["autopaste.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "AutoPaste.icns",
    "plist": {
        "CFBundleName": "AutoPaste",
        "CFBundleDisplayName": "AutoPaste",
        "CFBundleIdentifier": "com.autopaste.app",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSUIElement": True,  # hide from dock, menu-bar-only app
        "NSAppleEventsUsageDescription": "AutoPaste needs to send keystrokes to paste text.",
    },
    "packages": ["objc", "AppKit", "Quartz", "PyObjCTools"],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
