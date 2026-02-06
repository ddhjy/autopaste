from setuptools import setup

APP = ["autopaste.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "AutoPaste.icns",
    "semi_standalone": True,
    "plist": {
        "CFBundleName": "AutoPaste",
        "CFBundleDisplayName": "AutoPaste",
        "CFBundleIdentifier": "com.autopaste.app",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSUIElement": True,
        "NSAppleEventsUsageDescription": "AutoPaste needs to send keystrokes to paste text.",
    },
    "packages": ["objc", "AppKit", "Quartz"],
    "includes": ["PyObjCTools", "PyObjCTools.AppHelper"],
    "excludes": [
        "zmq", "IPython", "jupyter", "notebook", "tkinter",
        "matplotlib", "numpy", "pandas", "scipy", "PIL",
        "cv2", "sklearn", "torch", "tensorflow",
        "setuptools", "pkg_resources", "packaging",
    ],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
