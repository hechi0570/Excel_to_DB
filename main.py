import pandas as pd
import numpy as np
import os, re
import shutil
from tidy_up_tables import  Find_files, ClearUpExcel, Tools
from conn_database import ConnDatabase


ffs = Find_files()

class Main:
    def __init__(self) -> None:
        pass

    def find_files(self, path:str):
        return ffs.get_files(path=path)

    # def 
