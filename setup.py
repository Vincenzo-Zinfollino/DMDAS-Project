
from distutils.core import setup
import py2exe 

setup(windows=[{"script":"main.py",
                "icon_resources": [(1, "Icona.ico")],
                "dest_base":"main"
                }],
        options={ 
            "py2exe":{
                        "packages": [
                            
                            "asyncore",
                            "base64",
                            "csv",
                            "math",
                            "queue",
                            "sys",
                            "tkinter",
                            "datetime",
                            "unittest",
                            "unicodedata",
                            "logging",
                            "matplotlib",
                            "io",
                            "time",
                            "threading",
                            "numpy",
                           

                        ]



            }


        }





)