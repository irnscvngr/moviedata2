from moviedata.services.updates import updater
import pandas as pd

ud = updater()
ud.update_letterboxd()