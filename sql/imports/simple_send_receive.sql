-- Simple SQL for send/receive data (users, messages, submissions, ratings)
-- Intended to be easy and minimal for import into SQLite.
-- Run: sqlite3 subbase.db < simple_send_receive.sql

PRAGMA foreign_keys = ON;

-- Simple schema
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT,
  role TEXT DEFAULT 'student'
);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY,
  user_id INTEGER,
  content TEXT,
  created_at TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

-- submissions represent a student sending text to the model and receiving a response
CREATE TABLE IF NOT EXISTS submissions (
  id INTEGER PRIMARY KEY,
  student_id INTEGER,
  text TEXT,
  ai_fixed_text TEXT,
  ai_grade REAL,
  ai_response TEXT, -- full JSON response from model (optional)
  created_at TEXT,
  FOREIGN KEY(student_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS ratings (
  id INTEGER PRIMARY KEY,
  submission_id INTEGER,
  user_id INTEGER,
  value REAL,
  feedback_type TEXT,
  created_at TEXT,
  FOREIGN KEY(submission_id) REFERENCES submissions(id),
  FOREIGN KEY(user_id) REFERENCES users(id)
);

-- Data inserts (from project data/*.json)

-- users
INSERT INTO users (id,username,password_hash,role) VALUES (1,'admin','scrypt:32768:8:1$Gs7XNSL0K7nTZzRZ$325818bec6cf174a9263abc083afbc52477a44a06693a4acb8618e1fa64394845f95331ae0ef2ec773fb43686501806c4edfb84dc2d1206a2b14e611354f701c','admin');
INSERT INTO users (id,username,password_hash,role) VALUES (2,'student_1','scrypt:32768:8:1$rivPsPk4KI8fXdnV$d5107fa1874f3c7e0ab4a3a542a393881078a723e6fb2c093c04d79ef0798c8c454ec0c4af1467251c0c33063f2dbdb31ccd3678aa36b01e4ee150bf1ada03ca','student');

-- messages (simple send/receive records)
INSERT INTO messages (id,user_id,content,created_at) VALUES (1,2,'هلا','2025-10-13T06:29:05.763924+00:00');

-- submissions (student -> model -> response)
INSERT INTO submissions (id,student_id,text,ai_fixed_text,ai_grade,ai_response,created_at) VALUES
  (1,2,'هلا','',NULL,NULL,'2025-10-17T16:10:19.399800+00:00'),
  (2,1,'ان المدرسه مكان مهم لكي يتعلم الطالب العلوم والمعارف المختلفه ولاكن هناك بعض الطلاب لايحبين الدراسه بسبب ان المعلم لايشرح بشكل جيد وايضا بعض الطلاب يضيع وقتهم في الالعاب، لذلك يجب على المدرسين ان يهتمو في الطلاب ويكون هنالك عقاب شديد للطلاب المهملين، وفي النهايه يمكن ان تصبح المدرسه افضل لو كان كل شخص يقوم بواجبه علي اكمل وجه','إن المدرسة مكان مهم لكي يتعلم الطالب العلوم والمعارف المختلفة، ولكن هناك بعض الطلاب الذين لا يحبون الدراسة بسبب أن المعلم لا يشرح بشكل جيد. وأيضًا، بعض الطلاب يضيعون وقتهم في الألعاب. لذلك، يجب على المدرسين أن يهتموا بالطلاب، ويكون هنالك عقاب شديد للطلاب المهملين. وفي النهاية، يمكن أن تصبح المدرسة أفضل لو كان كل شخص يقوم بواجبه على أكمل وجه.',7.2,NULL,'2025-10-20T08:14:36.023229+00:00'),
  (3,1,'في هذا العصر الحديث اصبحت التكنولوجيا هي كل شي في حياتنا واصبح الناس لايستطعون ان يعيشون بدون الجوالات والبرامج لانها تسههل عليهم الاعمال ولكن بعض الاشخاص يستخدومنها بشكل غير صحيح مما يسبب في ضياع الوقت وقلت الانتباه، لذا يجب على المجتمع ان يوعي الشباب على استخدام التقنيه بالطريقه الصحيحه وعدم الافراط فيها لانها تضيع المستقبل وتجعل الطالب لايهتم في دراسته واخلاقه تصبح ضعيفه مع الوقت','في هذا العصر الحديث أصبحت التكنولوجيا جزءًا أساسيًا من حياتنا؛ فقد صار الناس لا يستطيعون العيش بدون الهواتف الذكية والتطبيقات، لأنها تُسهِّل عليهم الأعمال. ومع ذلك، يستخدم بعض الأشخاص هذه الوسائل بشكلٍ غير صحيح، مما يسبِّب ضياع الوقت وتشتُّت الانتباه. لذا يجب على المجتمع توعية الشباب بكيفية استخدام التقنية بالطريقة الصحيحة وعدم الإفراط فيها؛ لأن ذلك يضع مستقبلهم في خطر ويجعل الطالب لا يهتم بدراسته، وتضعُف أخلاقه مع الوقت.',4.9,NULL,'2025-10-20T08:38:45.468234+00:00'),
  (4,1,'صار العالم اليوم قرية صغيره بفضل التطور السريعة في وسائل التواصل، وصار الناس يتبادلون المعلومات بدون حدود ولا قيود ومع الاسف الكثير من الشباب يقضون وقت طويل في مشاهدة المقاطع التي لا تفيدهم بشي، بدل من ان يستغلون وقتهم في الدراسه أو تطوير مهاراتهم، واصبح البعض ينام متاخر بسبب الجوال وهذا الشي يؤثر على الصحه وعلى مستواهم في المدرسه، فيجب على الطالب ان يرتب وقتة ويعرف كيف يستخدمة بشكل صح حتى ينجح في حياته.','أصبح العالم اليوم قريةً صغيرةً بفضل التقدّم السريع في وسائل الاتصال؛ ويتبادل الناس المعلومات بلا حدود أو قيود. ومع الأسف، يقضي كثير من الشباب وقتًا طويلاً في مشاهدة مقاطع لا تفيدهم، بدل أن يستغلّوا أوقاتهم في الدراسة أو تطوير مهاراتهم. كما أصبح البعض ينام متأخّرًا بسبب الهاتف المحمول، وهذا الأمر يؤثّر في صحتهم وعلى تحصيلهم الدراسي. لذلك يجب على الطالب أن يرتّب وقته ويعرف كيف يستخدمه بشكل صحيح حتى ينجح في حياته.',5.2,NULL,'2025-10-20T08:44:48.156676+00:00'),
  (5,2,'انا ذهبت الى المدرسه امس مع اصدقائي، وكان في هناك درس مهم لكن ما فهمت لان المعلم يشرح بسرعه كثير. بعدين رجعنا البيت ولعبت كوره في الشارع، وبعدين امي قالت لي ليش ما تذاكر دروسك بدري، فانا قلت لها مافي واجبات اصلاً وهيه زعلت مني. انا لازم اصير طالب كويس عشان انجح في الحياه بس انا ما احب الدراسه كثير.','ذهبتُ إلى المدرسةِ أمسَ مع أصدقائي. كان هناك درسٌ مهمّ، لكنّي لم أفهمه لأنَّ المعلمَ يشرح بسرعةٍ كبيرة. بعد ذلك عدنا إلى البيت، ولعبتُ كرةً في الشارع. ثم قالت لي أمي: «لماذا لا تذاكر دروسَكَ مبكّرًا؟» فقلتُ لها إنّني لا أملك واجباتٍ أصلاً، فغضبتْ مني. يجب أن أكون طالبًا مجتهدًا لأنجحَ في الحياة، لكنّني لا أحبّ الدراسةَ كثيرًا.',6.1,NULL,'2025-10-21T07:28:19.556264+00:00');

-- ratings
INSERT INTO ratings (id,submission_id,user_id,value,feedback_type,created_at) VALUES (1,3,1,0,'not_helpful','2025-10-17T17:48:16.378362+00:00');
INSERT INTO ratings (id,submission_id,user_id,value,feedback_type,created_at) VALUES (2,4,1,0,'not_helpful','2025-10-20T16:30:15.668705+00:00');
