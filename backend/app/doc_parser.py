import asyncio,logging
from app.cpt_parser import analyze_cpt_file, analyze_cpt_file_with_llm
class AutoFlushFileHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

log_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
file_handler = AutoFlushFileHandler(r"E:\Workspaces\dataagent\agent_test.log", encoding="utf-8")
file_handler.setFormatter(logging.Formatter(log_fmt))
logger = logging.getLogger("app.cpt_parser.llm_enricher")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

# result = asyncio.run(analyze_cpt_file(r"E:\Docs\DataAgent_语义层解析\tf_pp_mfg_trc_mes_xjd.cpt"))
result = analyze_cpt_file(r"E:\Docs\DataAgent_语义层解析\tf_pp_mfg_trc_mes_xjd.cpt")
for ds_name, ds in result.datasets.items():
    print(f"\n{'='*60}")
    print(f"Dataset: {ds_name}")
    print(f"{'='*60}")

    print(f"\n--- Physical Tables ({len(ds.physical_tables)}) ---")
    for pt in ds.physical_tables:
        print(f"  {pt.schema}.{pt.name}" if pt.schema else f"  {pt.name}")

    print(f"\n--- Physical Joins ({len(ds.physical_joins)}) ---")
    for pj in ds.physical_joins:
        print(f"  {pj.left_table} {pj.join_type} {pj.right_table}"
              + (f" ON {pj.condition}" if pj.condition else "")
              + f" [source: {pj.source}]")