import pandas as pd
import subprocess
from datetime import datetime, timedelta

twitter_auth_token = '482a2580e4f6d92c414edb857b69b54f2a1efd33'

listOfProducts = ["drone", "tablet", "printer"]
current_date = datetime.now()
previous_date = current_date - timedelta(days=1)
day = previous_date.day
month = previous_date.month
year = previous_date.year
limit = 100
filename = f'combined_{previous_date.strftime("%Y-%m-%d")}.csv'

file_exists = False

for product in listOfProducts:
    search_keyword = f'{product} lang:id since:{year}-{month:02d}-{day:02d} until:{year}-{month:02d}-{day+1:02d}'
    temp_filename = f'temp_{product}.csv'
    
    subprocess.run(f'npx --yes tweet-harvest@2.6.1 -o "{temp_filename}" -s "{search_keyword}" --tab "LATEST" -l {limit} --token {twitter_auth_token}', shell=True)
    
    if not file_exists:
        df = pd.read_csv(temp_filename)
        df.to_csv(filename, index=False)
        file_exists = True
    else:
        df_temp = pd.read_csv(temp_filename)
        df_combined = pd.read_csv(filename)
        df_combined = pd.concat([df_combined, df_temp], ignore_index=True)
        df_combined.to_csv(filename, index=False)
