import os
import pandas as pd

# === Configuration ===
DATA_DIR = "game_data"
EXCEL_SUFFIX = "_analysis.xlsx"
OUTPUT_FILE = "merged_game_data.xlsx"
TOP_N = 100  # number of top other games to include


def discover_files(data_dir, suffix):
    return [f for f in os.listdir(data_dir) if f.endswith(suffix)]


def merge_kpis(files, suffix):
    rows = []
    for fname in files:
        path = os.path.join(DATA_DIR, fname)
        df = pd.read_excel(path, sheet_name='KPIs')
        row = df.iloc[0].to_dict()
        base = fname.replace(suffix, '').replace('_', ' ')
        row['base_game'] = base
        rows.append(row)
    kpi_df = pd.DataFrame(rows)
    cols = ['base_game'] + [c for c in kpi_df.columns if c != 'base_game']
    return kpi_df[cols]


def merge_other_games(files, top_n, suffix):
    rows = []
    for fname in files:
        path = os.path.join(DATA_DIR, fname)
        df = pd.read_excel(path, sheet_name='Other Games')
        base = fname.replace(suffix, '').replace('_', ' ')
        if 'steamid' in df.columns:
            df = df.drop(columns=['steamid'])
        avg = df.mean().sort_values(ascending=False).head(top_n)
        row = {'base_game': base}
        row.update(avg.to_dict())
        rows.append(row)
    other_df = pd.DataFrame(rows).fillna(0)
    cols = ['base_game'] + [c for c in other_df.columns if c != 'base_game']
    return other_df[cols]


def main():
    files = discover_files(DATA_DIR, EXCEL_SUFFIX)
    if not files:
        print(f"No '*{EXCEL_SUFFIX}' files found in {DATA_DIR}")
        return

    print(f"Merging {len(files)} analysis files...")
    kpi_df = merge_kpis(files, EXCEL_SUFFIX)
    other_df = merge_other_games(files, TOP_N, EXCEL_SUFFIX)

    print(f"Writing merged output to {OUTPUT_FILE}")
    with pd.ExcelWriter(OUTPUT_FILE) as writer:
        kpi_df.to_excel(writer, sheet_name='All KPIs', index=False)
        other_df.to_excel(writer, sheet_name='Top Other Games', index=False)

    # Export txt versions (tab-separated)
    kpi_txt = OUTPUT_FILE.replace('.xlsx', '_all_kpis.txt')
    other_txt = OUTPUT_FILE.replace('.xlsx', '_top_other_games.txt')
    kpi_df.to_csv(kpi_txt, sep='\t', index=False)
    other_df.to_csv(other_txt, sep='\t', index=False)
    print(f"Also wrote {kpi_txt} and {other_txt}")

    print("Done.")


if __name__ == '__main__':
    main()
