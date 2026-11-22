## 資料表總覽

跨表一致性要靠程式檢查。 評審所屬的會議必須和提名所屬獎項的會議相同

| 資料表 | 說明 |
|---|---|
| `meeting` | 會議基本資料 |
| `prize` | 獎項資料 |
| `manager` | 上司資料 |
| `employee` | 下屬資料 |
| `nominate` | 提名資料 |
| `judge` | 評審資料 |
| `vote` | 投票資料 |

## meeting

投票開始後不得修改門檻比例、人數上限、開始與截止時間
開始時間必須早於截止時間

| 欄位 | 型別 | Nullable | 說明 |
|---|---|:---:|---|
| `id` | int | | 主鍵 |
| `name` | str | | 會議名稱 |
| `total_judges` | int | | 總評審人數上限 |
| `total_budget` | int | | 總預算 |
| `proportion` | float | | 該提名通過門檻比例(0<x<=1, 預設是0.75, 該提名通過評審人數/該會議的評審總數，並以截止時的結果為準) |
| `voting_kickoff` | int | | 投票開始日期 (timestamp) |
| `voting_deadline` | int | | 投票截止日期 (timestamp) |
| `created_at` | int | | 創建時間 (timestamp) |

## prize

投票開始後，任何人都不得增刪該獎項的提名，這樣 N 才會固定
評審送出選票後不得修改

| 欄位 | 型別 | Nullable | 說明 |
|---|---|:---:|---|
| `id` | int | | 主鍵 |
| `name` | str | | 獎項名稱 |
| `meeting_id` | int | | 所屬會議（FK → meeting） |
| `created_at` | int | | 創建時間 (timestamp) |

## manager
| 欄位 | 型別 | Nullable | 說明 |
|---|---|:---:|---|
| `id` | int | | 主鍵 |
| `name` | str | | 上司名稱 |
| `created_at` | int | | 創建時間 (timestamp) |

## employee
| 欄位 | 型別 | Nullable | 說明 |
|---|---|:---:|---|
| `id` | int | | 主鍵 |
| `manager_id` | int | | 所屬上司（FK → manager） |
| `name` | str | | 下屬名稱 |
| `created_at` | int | | 創建時間 (timestamp) |

## nominate

每次送出選票時更新
允許總得分和平均序位存在，即使兩個指標是完全線性相關的*
排名預設以平均序位為主，先以門檻分組再排序，平均序位相同時並列同一名次

| 欄位 | 型別 | Nullable | 說明 |
|---|---|:---:|---|
| `id` | int | | 主鍵 |
| `prize_id` | int | | 所屬獎項（FK → prize） |
| `manager_name` | str | | 上司名稱 |
| `employee_name` | str | | 下屬名稱 |
| `name` | str | | 提名名稱 |
| `total_score` | float | ✓ | 序位總得分，該提名所有評審投票的得分進行加總 |
| `sort_average` | float | ✓ | 平均序位，該提名所有評審投票的排序取平均 |
| `threshold` | int | ✓ | 截止前的 threshold 會顯示一個暫時的值，通過人數大於等於評審總數乘以比例時為 1，否則為 0 |
| `issue_bonus` | int | ✓ | 核定獎金 |
| `deduct_instant_bonus` | int | ✓ | 扣除即時獎金 |
| `comment` | str | ✓ | 備註 |
| `created_at` | int | | 創建時間 (timestamp) |
| `updated_at` | int | | 更新時間 (timestamp) |

## judge

新增評審時不能超過會議的人數上限
投票開始後不得增刪評審

| 欄位 | 型別 | Nullable | 說明 |
|---|---|:---:|---|
| `id` | int | | 主鍵 |
| `name` | str | | 評審名稱 |
| `meeting_id` | int | | 所屬會議（FK → meeting） |
| `created_at` | int | | 創建時間 (timestamp) |

## vote

允許 sort 的「未通過」會和「最後一名」撞值*
截止時間後送出的選票一律拒收，開始前也拒收。

| 欄位 | 型別 | Nullable | 說明 |
|---|---|:---:|---|
| `id` | int | | 主鍵 |
| `judge_id` | int | | 所屬評審（FK → judge） |
| `nominate_id` | int | | 所屬提名（FK → nominate） |
| `pass` | int | | 該提名是否有通過 |
| `sort` | int | | 例子: 該獎項的總提名數當 N，提名通過且排序第一的排序值為 1，提名通過且排序第二的排序值為 2，以此類推，提名未通過的排序值都為 N |
| `score` | float | | 例子: 該獎項的總提名數當 N，提名通過且排序第一的分數為 (N-0)/N，提名通過且排序第二的分數為 (N-1)/N，以此類推，提名未通過的分數都為 (N-N)/N |
| `created_at` | int | | 創建時間 (timestamp) |
