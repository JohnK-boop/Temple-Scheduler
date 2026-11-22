"Window for agents to put information that can be shared with other agents."
##Not USED!!
# ===== 共有する state のキー名（全員共通）=====
USER_REQUEST = "user_request"   # chat_agent    が書く: 分析したい内容
DATA_RESULT = "data_result"     # data_agent    が書く: 準備したテーブル名など
MODEL_RESULT = "model_result"   # model_agent   が書く: 学習・評価結果
REPORT = "report"               # report_writer が書く: 最終レポート
RUN_HISTORY = "run_history"     # オーケストレーターが自動で書く
CSV_URI = "csv_uri"             # upload_csv gs:// path to the uploaded CSV
CSV_NAME = "csv_name"           # upload_csv clean name for table name
TARGET_COLUMN = "target_column" # chat_agent writes: column the user wants to predict
MODEL_TYPE = "model_type"       # chat_agent writes: model type the user chose