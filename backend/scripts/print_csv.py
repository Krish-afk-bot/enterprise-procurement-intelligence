import pandas as pd
df = pd.read_csv('data/real_procurement_ocds/sample/selected_sample.csv')
for i, row in df.iterrows():
    print(f"[{i+1}] {row['ocid']} | {row['buyer_name']} | {row['tender_title']} | Val: {row['value_amount']}")
