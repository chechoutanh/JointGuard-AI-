# 🤖 JointGuard AI: Bảo trì dự đoán cho khớp robot công nghiệp

**JointGuard AI là** dự án nghiên cứu nhằm ước lượng thời điểm một khớp robot công nghiệp cần bảo trì. Dự án dựa vào tín hiệu bên trong máy, như ma sát, mô-men và nhiệt độ, thay vì chỉ dùng camera. Dự án có hai nguồn dữ liệu tách biệt. Nguồn thứ nhất là dữ liệu thật từ các bệ thử ổ lăn và hộp số, dùng để xây dựng và đánh giá phương pháp. Nguồn thứ hai là một cánh tay KUKA iiwa mô phỏng bằng PyBullet: mài mòn được đưa vào thủ công, nên mỗi bộ dữ liệu vận hành sinh ra đều có sẵn đáp án để kiểm tra. Phiên bản hiện tại đã có pipeline dữ liệu, các baseline RUL, bộ mô phỏng, chỉ số sức khỏe theo khớp và dashboard. **Dự án chưa có mô hình RUL, chưa có bộ phát hiện lỗi, chưa dự báo ngày bảo trì và chưa chạy trên robot thật.**

*JointGuard AI is a research project for estimating when an industrial robot joint will need maintenance. It relies on signals from inside the machine, such as friction, torque and temperature, rather than on cameras alone. It uses two separate kinds of data. Real data from bearing and gearbox test rigs is used to build and evaluate the method. A PyBullet simulation of a KUKA iiwa arm, with wear injected by hand, produces operating data whose ground truth is known. The current version provides the data pipeline, RUL baselines, the simulator, a per-joint health index and an offline dashboard. **There is no RUL model, no fault detector and no maintenance-day forecast yet, and nothing has been run on a real robot.***

> Trạng thái theo tài liệu trong repo, cập nhật đến ngày 12/10/2026 (docs/GUIDE.md, docs/LIMITS.md, results/LOG.md).

---

## 🎯 Bài toán và mục tiêu

Một khớp robot hỏng đột ngột có thể làm dừng cả dây chuyền. Bảo trì theo lịch cố định thường tốn kém: khớp còn tốt vẫn bị can thiệp, còn khớp mòn nhanh có thể hỏng trước kỳ bảo trì. Mục tiêu của dự án là theo dõi tình trạng từng khớp từ tín hiệu bên trong máy, rồi kết hợp với lịch sản xuất để ước lượng ngày cần bảo trì.

Dự án chia thành ba câu hỏi riêng. Mỗi câu hỏi dùng một loại dữ liệu khác nhau, và kết quả của câu hỏi này không được dùng để trả lời câu hỏi kia:

| Phần | Câu hỏi | Dữ liệu | Trạng thái |
| :---- | :---- | :---- | :---- |
| rul/ | Ổ lăn này còn bao nhiêu phần tuổi thọ? | XJTU-SY (phát triển); IMS và KAIST (kiểm tra cuối, chạy một lần) | Đã có khung đánh giá và 3 baseline; **chưa có mô hình** |
| faults/ | Có gì bất thường không, và là loại lỗi nào? | SEU, CWRU | Đã có bộ đọc dữ liệu; **chưa xây bộ phân loại hay bộ phát hiện bất thường** |
| robot/ | Khi nào khớp robot mô phỏng này cần bảo trì? | Chỉ dữ liệu sinh từ PyBullet | Đã có mô phỏng, dữ liệu, chỉ số sức khỏe và dashboard; **chưa có dự báo** |

**Vai trò của mô phỏng.** Hiện chưa có dữ liệu từ robot thật được theo dõi đến khi cần bảo trì. Mô phỏng tạo ra dữ liệu với mức mài mòn đã biết trước, nhờ đó kiểm tra được toàn bộ pipeline từ đầu đến cuối. Đổi lại, mọi độ chính xác đo trong mô phỏng đều đúng *theo cách dựng*: chương trình đưa mài mòn vào rồi tự đọc lại bằng cùng mô hình vật lý.

**Phạm vi hiện tại.** Tuyên bố trung thực cho toàn dự án là: phương pháp được kiểm chứng trên dữ liệu ổ lăn và hộp số thật, còn pipeline chạy được từ đầu đến cuối trên một khớp robot mô phỏng. Dự án chưa kiểm chứng trên robot thật. Dữ liệu ổ lăn và hộp số **không phải** telemetry của robot.

---

## ✨ Tính năng chính

Chú thích: ✅ đã triển khai · 🧪 đã xây nhưng đang tắt hoặc chỉ dùng trong thí nghiệm · ⏳ chưa xây dựng

| Tính năng | Mô tả | Trạng thái |
| :---- | :---- | :---- |
| Bộ đọc 5 bộ dữ liệu | XJTU-SY, IMS, KAIST, SEU và CWRU được đưa về chung một kiểu Recording. Mỗi lần chỉ đọc một snapshot từ đĩa | ✅ |
| Đặc trưng rung | 10 đặc trưng cho mỗi cảm biến (rms, peak, kurtosis, crest, 5 dải tần tính theo Hz, tần số trọng tâm). Mỗi đặc trưng được so với giai đoạn khỏe ban đầu của chính ổ lăn đó | ✅ (mới trích xuất và lưu cache cho XJTU-SY) |
| Khung đánh giá RUL | Mục tiêu là phần tuổi thọ còn lại, dùng 2 cách chia dữ liệu (bỏ một ổ lăn, bỏ một điều kiện) và 8 thước đo. Có test kiểm tra không dùng thông tin tương lai | ✅ |
| 3 baseline RUL | Hằng số 0.5, dựa theo thời gian chạy, và bảng tra theo rms | ✅ |
| Mô hình RUL | Mô hình phải vượt các baseline theo quy tắc chấp nhận đã viết sẵn | ⏳ |
| Phân loại lỗi và phát hiện bất thường (SEU, CWRU) | Mới có bộ đọc dữ liệu và test | ⏳ |
| Kiểm tra cuối trên IMS và KAIST | Chỉ chạy một lần, sau khi mô hình đã cố định | ⏳ |
| Mô phỏng KUKA iiwa trong PyBullet | Ma sát Stribeck và ma sát nhớt, mài mòn tăng theo khối lượng công việc, nhiệt độ khớp | ✅ |
| Bài quét kiểm tra sức khỏe (health-check sweep) | Quay một khớp ở 18 tốc độ không đổi, trừ trọng lực, rồi fit ma sát Coulomb và ma sát nhớt | ✅ |
| Vòng lặp theo ngày và lịch sản xuất | 2 kịch bản tải, mỗi kịch bản 5 robot có tốc độ mòn khác nhau, quét mỗi ngày | ✅ |
| Tách đáp án và chống rò rỉ | Mức mài mòn ẩn chỉ nằm trong ground\_truth.csv. Một bộ kiểm tra (guard) từ chối file sweep nếu có cột mài mòn | ✅ |
| Chỉ số sức khỏe theo khớp | So ma sát Coulomb hiện tại với tuần đầu của chính khớp đó, có bù nhiệt độ | ✅ (dùng hệ số của mô phỏng, xem phần Giới hạn) |
| 5 công tắc "độ thực tế" | Nhiễu mài mòn, mòn tăng tốc cuối đời, mòn làm tăng ma sát nhớt, sai số khối lượng mô hình, lỗi cảm biến | 🧪 đã xây và đo ảnh hưởng, **tắt mặc định** |
| Sự kiện bảo trì (tra mỡ lại) | Giảm mài mòn của khớp và ghi vào events.csv | 🧪 có code và test, chưa có trong kịch bản nào |
| Demo trực quan | Mở cửa sổ PyBullet, quét một khớp với mức mòn nhập từ dòng lệnh, in chỉ số sức khỏe | ✅ (chỉ một lần quét, không có thanh trượt) |
| Dashboard HTML | Mỗi kịch bản một file HTML tự chứa, mở offline, có bộ lọc robot/khớp/ngày và công tắc hiện đáp án | ✅ |
| Cờ "service due" trên dashboard | Quy tắc ngưỡng: bật khi chỉ số sức khỏe chạm 0.8. Đây không phải dự báo | ✅ |
| Dự báo ngày bảo trì theo lịch sản xuất | Hồi quy tốc độ mòn theo khối lượng công việc, tích phân theo kế hoạch | ⏳ (chỉ có một bản tạm làm "thước đo" trong script thí nghiệm) |
| Cảnh báo thời gian thực, chạy trên robot thật | — | ⏳ chưa nằm trong phạm vi |

---

## 🚀 Cài đặt và cách chạy

**Môi trường.** Conda, Python 3.10. Các thư viện gồm numpy, scipy, pandas, scikit-learn, matplotlib-base, pybullet, pyarrow và pytest. Môi trường này không dùng PyTorch, PyQt hay web framework.

conda env create \-f environment.yml

conda activate pdm

python \-m pytest tests \-q          \# chỉ dùng dữ liệu tổng hợp, không cần tải dataset

### Phần robot mô phỏng (không cần dữ liệu ngoài)

\# Demo trực quan: quét khớp 3 với mức mòn 0.5 trong cửa sổ PyBullet và in chỉ số sức khỏe

python \-m tools.robot demo \--gui \--joint 3 \--wear 0.5

\# Sinh bộ dữ liệu: 5 robot, mỗi robot 850 ngày, ghi vào data/simulation/ramp\_early/run\_\<k\>/

python \-m tools.robot demo \--scenario ramp\_early \--days 850 \--seed 0 \--runs 5

python \-m tools.robot demo \--scenario ramp\_late  \--days 1450 \--seed 0 \--runs 5

\# Dashboard HTML, ghi vào results/robot/dashboard\_\<scenario\>.html

python \-m tools.dashboard \--scenario ramp\_early

python \-m tools.dashboard \--scenario ramp\_late \--no-truth   \# bỏ hẳn đáp án khỏi file

Mở trực tiếp một góc nhìn của dashboard bằng tham số URL, ví dụ: dashboard\_ramp\_early.html?run=2\&joint=4\&day=600\&truth=1\&theme=dark.

### Phần ổ lăn (cần dữ liệu gốc)

Đặt dữ liệu gốc vào data/external/ theo cấu trúc mô tả trong docs/DATASETS.md. Repo không chứa dữ liệu gốc.

python \-m tools.sources            \# liệt kê những gì mỗi bộ đọc tìm thấy trên đĩa

python \-m tools.features xjtu      \# trích xuất đặc trưng và lưu cache vào data/processed/ (--force để làm lại)

python \-m tools.rul evaluate       \# đánh giá 3 baseline trên XJTU-SY

### Thời gian chạy đã ghi nhận

Các con số dưới đây đo trên máy Mac của tác giả, chỉ để tham khảo:

| Tác vụ | Thời gian |
| :---- | :---- |
| Bộ test | khoảng 17 s |
| tools.sources | khoảng 8 s |
| Trích xuất đặc trưng XJTU-SY (9216 snapshot) | 69 s |
| tools.rul evaluate | dưới 1 s |
| Một ngày mô phỏng (quét 6 khớp) | 0.32 s thời gian máy |
| 10 lần chạy của hai kịch bản | 63 phút thời gian máy |
| Demo GUI một lần quét | khoảng 29 s (chiếu chậm 5 lần so với thời gian thực) |

> legacy/robot\_simulator\_8/ là bộ mô phỏng PyQt của dự án trước, chỉ được giữ lại để tham khảo. Nó cần môi trường riêng (xem legacy/README.md), không được dự án này import, và các con số của nó không phải kết quả của dự án.

---

## ⚙️ Mô phỏng và luồng xử lý dữ liệu

### Robot và cách điều khiển

- **Robot:** kuka\_iiwa/model.urdf lấy từ pybullet\_data, gắn cố định vào đế. Bài quét dùng 6 khớp (0 đến 5). Thí nghiệm chạy ở chế độ DIRECT, không có cửa sổ; cửa sổ GUI chỉ dùng cho demo.  
- **Bước thời gian:** 1/1000 s khi quét.  
- **Khớp đang quét:** tắt motor vận tốc mặc định của PyBullet (VELOCITY\_CONTROL, force=0), rồi điều khiển khớp bằng TORQUE\_CONTROL với vòng điều khiển tốc độ tỉ lệ (P). Hệ số khuếch đại được nhân với quán tính của khớp, lấy từ đường chéo ma trận khối lượng.  
- **Các khớp còn lại:** khóa bằng motor vị trí của PyBullet, giống như phanh giữ khớp. Khi giữ bằng mô-men PD tính trong Python như bản đặc tả ban đầu, các khớp này bị trôi đến giới hạn tốc độ của PyBullet (docs/GUIDE.md, mục 6).  
- **Damping sẵn có của file URDF được đặt về 0\.** Nếu giữ nguyên, ma sát nhớt đo được của một khớp cổ tay sai đến 4419%.

### Mô hình hao mòn (phần "ẩn")

- **Ma sát:** Stribeck cộng ma sát nhớt. Dùng tanh(v/eps) thay cho sign(v) để tránh đổi dấu đột ngột quanh v \= 0\. Độ lớn ma sát được chọn theo quán tính của từng khớp, vì quán tính các khớp chênh nhau khoảng 4000 lần.  
- **Mài mòn:** dW/dt \= k·u(t), với u là khối lượng công việc (duty) *thực tế*. Ma sát Coulomb tăng theo W. Mỗi robot có hệ số tốc độ mòn riêng, chênh khoảng 15% giữa các robot.  
- **Nhiệt độ:** mô hình một dòng. Mỗi ngày nhiệt độ khớp tiến 0.7 quãng đường về 26 °C \+ 15 °C × duty. Khớp nóng hơn thì ma sát thấp hơn, khoảng 0.8% mỗi độ.  
- **Lịch sản xuất:** một mẫu cố định gồm mức tải × mẫu theo tuần × các giai đoạn bận và rảnh. Duty thực tế bằng duty kế hoạch nhân với nhiễu khoảng 18%, có trung bình bằng 1\.  
- **Hai kịch bản:** ramp\_early tăng gấp đôi tải từ ngày 200, trước khi bất kỳ khớp nào cần bảo trì. ramp\_late tăng gấp đôi tải từ ngày 1500, tức là không xảy ra trong độ dài các lần chạy.

### Bài quét kiểm tra sức khỏe

Mỗi ngày, mỗi khớp được quét ở 18 tốc độ không đổi, 9 tốc độ mỗi chiều, bắt đầu từ 0.10 lần tốc độ định mức. Ở mỗi tốc độ, khớp được giữ 0.1 s để ổn định và 0.1 s để đo.

| Đại lượng | Nguồn |
| :---- | :---- |
| Góc và vận tốc khớp | Đọc trực tiếp từ PyBullet |
| Mô-men lệnh | Do bộ điều khiển tốc độ đặt (TORQUE\_CONTROL) |
| Mô-men trọng lực | Tính bằng calculateInverseDynamics(q, 0, 0\) |
| **Mô-men ma sát** | **Tính toán:** mô-men lệnh − mô-men trọng lực, cộng nhiễu cảm biến (1.1% ma sát Coulomb, phân bố chuẩn) |
| Fc (Coulomb), Fv (nhớt) | Tính toán: hồi quy τ \= Fc·sign(v) \+ Fv·v, chỉ trên các điểm có |v| ≥ 0.08 lần tốc độ định mức |
| Nhiệt độ khớp | Theo mô hình nhiệt giả định ở trên |
| Duty kế hoạch | Theo lịch sản xuất. Đây là duty duy nhất có trong file dữ liệu |
| Mức mài mòn W | **Ẩn**, chỉ ghi vào ground\_truth.csv |

Phần robot không dùng gia tốc, công suất, lực tiếp xúc hay tín hiệu rung.

### Luồng xử lý

Lịch sản xuất ──► duty kế hoạch ──► duty thực tế (nhiễu \~18%)

                                         │

                                         ▼

                              mài mòn W (ẩn) ──► ground\_truth.csv  (đáp án, không cho mô hình đọc)

                                         │

                                         ▼

          ma sát Stribeck \+ nhớt, phụ thuộc W và nhiệt độ (PyBullet, DIRECT, dt \= 1 ms)

                                         │

                                         ▼

        Bài quét mỗi ngày: 6 khớp × 18 tốc độ ──► mô-men ma sát \= lệnh − trọng lực

                                         │

                                         ▼

               sweeps.parquet  (+ schedule.csv, actual\_duty.csv, events.csv)

                     │   guard: từ chối nếu file có cột mài mòn

                     ▼

     robot/health.py: fit Fc ─► chỉ số sức khỏe theo khớp (bù nhiệt, không nhìn trước)

                     │

                     ▼

     tools.dashboard: HTML offline, cờ "service due" khi chỉ số ≥ 0.8

                     │

                     ▼

     \[chưa xây\] dự báo ngày bảo trì từ tốc độ mòn và lịch sản xuất kế hoạch

Mỗi thư mục data/simulation/\<scenario\>/run\_\<k\>/ chứa 5 file sau:

| File | Nội dung |
| :---- | :---- |
| sweeps.parquet | Mỗi dòng là một (ngày, khớp, tốc độ). Đây là bộ dữ liệu cho mô hình, và không chứa mức mài mòn |
| schedule.csv | Duty kế hoạch của từng ngày |
| actual\_duty.csv | Duty thực tế. Hiện **chưa quyết định** mô hình có được đọc file này hay không |
| events.csv | Nhật ký bảo trì (trống trong cả hai kịch bản) |
| ground\_truth.csv | Mức mòn ẩn và ngày cần bảo trì thật của từng khớp. Đây là đáp án |

---

## 🧠 Thuật toán và học máy

**Hiện chưa có mô hình học máy nào được huấn luyện trong dự án.** Các thành phần đang chạy là các phép tính thống kê và vật lý đơn giản, mô tả đúng như sau:

| Thành phần | Bản chất | Đầu ra |
| :---- | :---- | :---- |
| Đặc trưng tương đối (features/) | Mỗi đặc trưng chia cho median của 10 snapshot đầu của chính ổ lăn. Mốc so sánh tính theo số snapshot, không theo phần trăm tuổi thọ, vì lúc dự đoán chưa biết tổng tuổi thọ | 10 tỉ số cho mỗi snapshot. Với nhiều cảm biến, giữ cảm biến thay đổi nhiều nhất |
| Baseline "hằng số" | Luôn dự đoán s \= 0.5 | Mốc của dự đoán không có thông tin (MAE 0.25) |
| Baseline "thời gian" | s \= 1 − giờ đã chạy / median tuổi thọ của các ổ lăn huấn luyện | Mốc của dự đoán chỉ dựa vào đồng hồ |
| Baseline "chỉ rms" | Bảng tra 10 nhóm theo rms tương đối, lập từ các ổ lăn huấn luyện. Mỗi nhóm trả về median s và khoảng chứa 90% | s và khoảng 90%. Đây là bảng tra thống kê, không phải mô hình học sâu |
| Fit ma sát (robot/fit.py) | Hồi quy tuyến tính 2 tham số | Fc, Fv |
| Chỉ số sức khỏe (robot/health.py) | (Fc / Fc của tuần đầu − 1\) / 1.5, có bù nhiệt. Mỗi ngày chỉ dùng ngày đó và tuần đầu | Một số cho mỗi khớp mỗi ngày. Theo thiết kế, giá trị này xấp xỉ mức mòn W |
| Cờ "service due" | Quy tắc ngưỡng: chỉ số ≥ 0.8 | Có hoặc không. **Không phải dự báo**, cũng không phải RUL |

**Các nguyên tắc đánh giá đã được cài sẵn:**

- Chia dữ liệu theo nguyên ổ lăn, không theo cửa sổ hay snapshot.  
- Mỗi dự đoán tại thời điểm t chỉ dùng dữ liệu đến t. Test test\_streaming\_predictions\_equal\_batch\_predictions kiểm tra điều này. Khi cố tình cho hai baseline nhìn trước, test đã báo lỗi cả hai lần.  
- Mọi bảng kết quả đều phải có cả 3 baseline.

**Kế hoạch cho phần chưa xây** (theo CLAUDE.md, chưa phải tính năng):

- **RUL:** một mô hình trên các đặc trưng tương đối. Mô hình chỉ được chấp nhận nếu MAE khi bỏ một ổ lăn cải thiện có ý nghĩa (khoảng tin cậy bootstrap ghép cặp 95% không chứa 0), MAE khi bỏ một điều kiện không xấu đi quá 0.005, và recall gần hỏng không giảm.  
- **Lỗi và bất thường:** bộ phát hiện chỉ huấn luyện trên cửa sổ khỏe, riêng theo từng điều kiện. Một cảnh báo cần 2 cửa sổ bị gắn cờ liên tiếp. Phải báo cáo cả tỉ lệ báo động giả lẫn tỉ lệ và độ trễ phát hiện.  
- **Dự báo cho robot:** hồi quy tốc độ mòn k theo duty tích lũy, tích phân theo lịch kế hoạch, lấy ngày đầu tiên vượt ngưỡng. Phương pháp này chỉ dùng numpy, ở dạng closed form, không dùng mạng nơ-ron. So sánh với baseline tốc độ không đổi và baseline ngoại suy tuyến tính, và đo độ nhạy khi kế hoạch lệch ±30%.

---

## 📊 Kết quả và kiểm thử

### 1\. Baseline RUL trên XJTU-SY (dữ liệu ổ lăn thật, 15 ổ lăn)

MAE là sai số của phần tuổi thọ còn lại s (từ 0 đến 1). Dự đoán luôn bằng 0.5 có MAE 0.25.

| Dự đoán | MAE (bỏ 1 ổ lăn) | MAE (bỏ 1 điều kiện) | Số ổ lăn có MAE \< 0.25 | Recall gần hỏng | Độ phủ khoảng 90% |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Hằng số 0.5 | 0.252 | 0.252 | 0/15 | 0.00 | 0.90 |
| Theo thời gian | 0.317 | 0.329 | 3/15 và 2/15 | 0.47 và 0.53 | 0.87 và 0.74 |
| Chỉ rms | **0.200** | **0.203** | 10/15 | 0.37 và 0.43 | 0.86 và 0.83 |

**Cách đọc.** "Chỉ rms" là baseline mạnh nhất nhưng vẫn yếu: chỉ tốt hơn dự đoán không thông tin 21%, và kém hơn mốc đó trên 5/15 ổ lăn (4 trong số đó ở 40 Hz). Recall gần hỏng có thể bị "ăn gian" bằng cách báo hỏng quá sớm, nên phải luôn đọc cùng MAE. Khoảng 90% của baseline chỉ phủ 0.83 đến 0.86, tức là chưa giữ đúng cam kết 90%. Đây là mốc mà mô hình RUL sau này phải vượt qua. **Các con số này nói về ổ lăn, không nói về robot.**

### 2\. Mô phỏng robot: các mốc kiểm chứng

Toàn bộ các con số trong mục này đến từ mô phỏng. Chương trình đưa mài mòn vào rồi đọc lại bằng cùng code, nên các con số chỉ chứng minh tính toán nhất quán, **không phải độ chính xác trên robot thật.**

| Mốc | Câu hỏi | Kết quả |
| :---- | :---- | :---- |
| M1: một lần quét | Bài quét có đọc lại được ma sát đã đưa vào không? | Fc khớp với giá trị đưa vào trong khoảng 0.7% trên 6/6 khớp (có nhiễu). Với W \= 0.8, chỉ số sức khỏe đọc được 0.798 đến 0.812 |
| M2: vòng lặp ngày | Cùng seed có cho file giống hệt không? Có rò rỉ đáp án không? | 5 file giống từng byte. Guard hoạt động đúng. Sau khi bù nhiệt, chỉ số bám mức mòn ẩn trong khoảng 0.003. Chưa bù nhiệt thì lệch đến 0.063 |
| M3: nhiều robot | Mọi khớp có chạm ngưỡng không? Mòn ở một khớp có ảnh hưởng sang khớp khác không? | 30/30 quỹ đạo khớp chạm ngưỡng trong mỗi kịch bản. Khi chỉ khớp 3 mòn, Fc khớp 3 tăng \+113.7%, các khớp khác thay đổi trong ±0.53% |
| M4: công tắc độ thực tế | Mỗi công tắc ảnh hưởng thế nào tới một dự báo đường thẳng? | Chỉ "mòn tăng tốc cuối đời" ảnh hưởng đáng kể: dự báo bị **trễ** trên 30/30 khớp, trung bình 11 ngày, tệ nhất 28 ngày. Các công tắc khác thay đổi sai số dưới 1 ngày |
| M5: demo trực quan | Cửa sổ có mở, và chỉ số in ra có đúng mức mòn đã nhập không? | Cửa sổ mở và in 0.51 cho W \= 0.5. Trên 6 khớp × 5 mức mòn, sai lệch tối đa là 0.021 |
| Dashboard | Trang có chạy không, và cờ "service due" có đúng không? | Trang tải và vẽ được trong Chrome headless, mọi điều khiển đều phản hồi. Cờ bật **muộn hơn** ngày bảo trì thật trung bình 4.0 ngày (ramp\_early) và 7.5 ngày (ramp\_late) |

Bộ dữ liệu hiện có: 2 kịch bản × 5 robot × 6 khớp, chạy 850 và 1450 ngày, tổng 1.242.000 dòng sweep, khoảng 25 MB. Ngày cần bảo trì của cùng một khớp chênh tới 509 ngày giữa các robot, nên không thể đoán ngày bảo trì chỉ từ số hiệu khớp.

Lưu ý về con số 11 ngày ở M4: đó là sai số của một "thước đo" tạm viết trong script thí nghiệm. Thước đo này còn dùng hệ số nhiệt độ thật của mô phỏng. Nó không phải dự báo của dự án, vì dự báo chưa được xây.

### 3\. Kiểm thử

- Bộ test chỉ dùng dữ liệu tổng hợp: 206 test, khoảng 17 s (docs/GUIDE.md, mục 11).  
- Mỗi phần mới đều được kiểm bằng cách cố tình cài lỗi vào code, mỗi lần một lỗi, để xem bộ test có bắt được không. Ví dụ: lấy trọng lực sai góc, dùng sign thay cho tanh, ghi duty thực tế vào file sweep, hoặc cho cả 6 khớp cùng một hệ số mòn. Bộ test hiện bắt được tất cả lỗi đã thử (20, 28, 12, 26, 11 và 20 lỗi ở các mốc tương ứng).  
- Bài kiểm tra cuối trên IMS và KAIST chưa chạy.  
- Phần phân loại lỗi và phát hiện bất thường chưa có kết quả định lượng nào.

---

## 🏗️ Kiến trúc

robot-pdm/

├── CLAUDE.md            quy tắc dự án: phạm vi, quy tắc đánh giá, lệnh chạy

├── config.py            mọi tham số của phần ổ lăn, kèm lý do

├── environment.yml      môi trường conda "pdm"

├── sources/             mỗi bộ dữ liệu một bộ đọc → Recording

│   ├── recording.py     kiểu dữ liệu chung, đọc snapshot lười từ đĩa

│   ├── xjtu.py  ims.py  kaist.py  seu\_cwru.py

├── features/            đặc trưng của một snapshot, đặc trưng tương đối, cache

├── rul/                 dữ liệu, 3 baseline, thước đo, đánh giá theo 2 cách chia

├── robot/               mô phỏng PyBullet (tham số riêng trong robot/config.py)

│   ├── world.py         nạp KUKA iiwa, tắt motor mặc định, khóa các khớp giữ

│   ├── friction.py      ma sát Stribeck \+ nhớt, phụ thuộc mòn và nhiệt độ

│   ├── sweep.py  fit.py bài quét 18 tốc độ và hồi quy Fc, Fv

│   ├── schedule.py      lịch sản xuất và 2 kịch bản

│   ├── thermal.py       mô hình nhiệt một dòng

│   ├── simulate.py      vòng lặp theo ngày, nhiều lần chạy, các công tắc độ thực tế

│   ├── collect.py       ghi 5 file dữ liệu của mỗi lần chạy

│   ├── guard.py         chặn file sweep có chứa mức mòn

│   ├── health.py        chỉ số sức khỏe từ các sweep đã lưu

│   └── checks.py  view.py   phần phụ trợ cho kiểm tra và demo GUI

├── tools/               điểm chạy dòng lệnh: sources, features, rul, robot, dashboard

│   └── dashboard\_template.html

├── tests/               26 file test, chỉ dùng dữ liệu tổng hợp

├── results/             mỗi thí nghiệm một thư mục (script, output thô, kết luận); LOG.md là mục lục

│   └── robot/           dashboard HTML, ảnh quét, ảnh vòng đời, ảnh demo

├── docs/

│   ├── GUIDE.md         từng thí nghiệm: quan sát, giả thuyết, số liệu, kết luận

│   ├── LIMITS.md        mọi điểm yếu, chưa kiểm chứng hoặc chỉ là mô phỏng

│   ├── DATASETS.md      nguồn, trích dẫn, giấy phép

│   └── CODE\_GUIDE.md    từng hàm viết thành các bước, để tự viết lại

├── data/

│   ├── external/        dữ liệu gốc (gitignore, không commit)

│   ├── processed/       đặc trưng đã cache (gitignore cho đến khi kiểm tra giấy phép)

│   └── simulation/      bộ dữ liệu robot mô phỏng

└── legacy/robot\_simulator\_8/   bộ mô phỏng PyQt của dự án trước, chỉ lưu lại

Dự án không có thư mục faults/, cũng không có lệnh tools.faults hay tools.final\_test. Đó là các bước chưa xây.

---

## ⚠️ Giới hạn

Danh sách đầy đủ nằm trong docs/LIMITS.md. Các điểm chính:

**Khoảng cách giữa mô phỏng và robot thật**

- Tham số ma sát, tốc độ định mức, tư thế và mức nhiễu đều được *chọn*, không được *đo* trên robot thật.  
- Trọng lực được trừ bằng chính mô hình mà mô phỏng dùng, nên triệt tiêu gần như tuyệt đối (sai khoảng 0.000007 N·m). Trên robot thật, mô hình động lực học không bao giờ chính xác như vậy.  
- Các khớp giữ bị khóa cứng, nên test "mòn ở khớp này không ảnh hưởng khớp khác" đạt được theo cách dựng.  
- Nhiễu cảm biến rất đơn giản: chỉ trên mô-men, phân bố chuẩn, không có điểm ngoại lai và không trôi (trừ khi bật công tắc lỗi cảm biến).  
- Chỉ số sức khỏe dùng hệ số khuếch đại mòn và hệ số nhiệt độ *của chính mô phỏng*. Hệ thống thật sẽ phải ước lượng cả hai. Nếu không bù nhiệt, chỉ số lệch đến 0.06, bằng 8% ngưỡng bảo trì.

**Dữ liệu mô phỏng quá gọn**

- Ở bộ dữ liệu hiện tại, mòn tỉ lệ đúng với khối lượng công việc và cảm biến không bao giờ hỏng. Cả 5 công tắc độ thực tế đều đang tắt.  
- Mòn tăng tốc cuối đời làm một dự báo đường thẳng trễ trên mọi khớp. Khi công tắc này tắt, điểm yếu đó không hiện ra trong dữ liệu.  
- Chỉ có 5 robot chứ không phải 10\. Lần chạy k của hai kịch bản dùng cùng seed, nên dữ liệu giống hệt nhau đến ngày 199\. 6 khớp trong cùng một lần chạy cũng chịu cùng lịch làm việc.  
- Không khớp nào được bảo trì trong các lần chạy, nên sau ngày cần bảo trì, mức mòn tiếp tục tăng đến 3.7. Không nên dùng các dòng dữ liệu sau ngày đó.  
- Lịch sản xuất là một mẫu tuần hoàn, trong khi kế hoạch thật không lặp lại như vậy.

**Phần ổ lăn**

- Chưa có mô hình. Baseline tốt nhất còn yếu, và khoảng 90% chưa đạt độ phủ 90%.  
- 15 ổ lăn XJTU-SY là ít. Tuổi thọ của chúng chênh nhau 60 lần (0.68 đến 42.3 giờ).  
- IMS chỉ có 3 lần chạy độc lập, KAIST chỉ có 1 ổ lăn. Ngày hỏng của IMS test 3 còn nghi vấn. Tác giả đã từng xem kết quả trên IMS và KAIST trong dự án trước, nên hai bộ này không còn hoàn toàn "sạch".  
- CWRU ghi file bình thường ở 48 kHz và file lỗi ở 12 kHz. Một bộ phân loại có thể tách "bình thường" với "lỗi" vì khác biệt cách ghi chứ không phải vì ổ lăn.  
- Mới kiểm tra giấy phép của KAIST (CC BY 4.0). Vì vậy chưa commit đặc trưng hay mô hình suy ra từ các bộ dữ liệu khác.

**Dashboard và demo**

- Dashboard cho biết khớp *đang ở đâu*, chưa cho biết *khi nào* cần bảo trì. Cờ "service due" bật muộn vài ngày so với thực tế.  
- Dashboard mới được kiểm bằng script trên Chrome ở độ rộng 1280 px, chưa có người dùng thật. Chưa thử Safari, Firefox, điện thoại hay màn hình cảm ứng.  
- Demo chỉ quét một lần, không có thanh trượt và không có dự báo.

---

## 🗺️ Hướng phát triển

Các mục dưới đây là kế hoạch, **chưa phải tính năng**. Hạn chót là các mốc đặt ra trong CLAUDE.md.

| Hạn | Việc cần làm |
| :---- | :---- |
| 20/10/2026 | Mô hình RUL so với 3 baseline, kèm kết luận chấp nhận hay loại theo quy tắc đã viết trước. Bộ phân loại lỗi và bộ phát hiện bất thường trên SEU/CWRU, với cách chia dữ liệu trung thực. Cố định mô hình RUL |
| 27/10/2026 | Dự báo ngày bảo trì cho robot: so với baseline tốc độ không đổi và ngoại suy tuyến tính, trên cả hai kịch bản, đo độ nhạy khi kế hoạch lệch ±30%. Chạy kiểm tra cuối trên IMS và KAIST đúng một lần |
| 1/11/2026 | Hoàn thiện README, GUIDE và LIMITS, quay video demo, nộp bài |

Các việc khác cần người dùng quyết định:

- Bật công tắc nào trong 5 công tắc độ thực tế. WEAR\_ACCEL là công tắc khiến bài toán dự báo khó và trung thực hơn.  
- Có cho mô hình đọc actual\_duty.csv hay không.  
- Có thêm sự kiện bảo trì vào kịch bản hay không.  
- Thu dữ liệu và thử trên robot một tay thật trong nhà máy. Mục này hiện nằm ngoài phạm vi.

---

## 🤖 Quy trình sử dụng AI

Dự án được xây dựng cùng **Claude Code** (Anthropic). Repo cho thấy cách làm việc như sau:

- **Phần do tác giả quyết định.** CLAUDE.md ghi phạm vi, quy tắc đánh giá, ràng buộc kỹ thuật, kế hoạch, và các việc phải hỏi tác giả trước: thêm thư viện, xóa file, commit, bật công tắc. Phần robot được xây theo các bản đặc tả sim.md và ROBOT\_SIM\_DATA\_SPEC.md. Ví dụ, dashboard được làm theo yêu cầu của tác giả ngày 12/10, và các lần chạy 400 ngày cũ bị xóa theo yêu cầu của tác giả.  
- **Vai trò của Claude Code.** Claude Code làm việc theo các quy tắc đó. docs/GUIDE.md được viết ở ngôi thứ nhất và ghi lại từng thí nghiệm: kỳ vọng viết trước khi chạy, số liệu, các chỗ kỳ vọng sai, và kết luận giữ hay loại.  
- **Cơ chế kiểm soát chất lượng.** Mỗi thí nghiệm lưu script và output thô trong results/. Mỗi phần code mới được kiểm bằng cách cố tình cài lỗi để thử bộ test. Mọi điểm yếu được ghi vào docs/LIMITS.md. docs/CODE\_GUIDE.md mô tả từng hàm dưới dạng các bước để tác giả có thể tự viết lại và giải thích được.

Để đọc phần mô phỏng, nên bắt đầu từ docs/GUIDE.md (mục 6 đến 11\) và các thư mục tương ứng trong results/.

---

## 📚 Dữ liệu và trích dẫn

Dự án dùng các bộ dữ liệu công khai XJTU-SY, IMS (NASA), KAIST, SEU và CWRU. Nguồn, cách trích dẫn và tình trạng giấy phép của từng bộ nằm trong docs/DATASETS.md. Dữ liệu gốc không được đưa vào repo.
