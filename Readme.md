# 🎤 Voice-to-SQL Assistant

An **AI-powered Natural Language to SQL (NL2SQL) assistant** with voice input/output.  
This project lets you **ask questions in plain English (or voice)** and receive **spoken + text answers** generated from a live SQL database.  

Built using:
- 🗄️ **SQLAlchemy + PostgreSQL** for database connectivity  
- 🧠 **LangChain + Ollama** for SQL generation & reasoning  
- 🎙️ **Faster-Whisper** for speech-to-text (STT)  
- 🗣️ **pyttsx3** for text-to-speech (TTS)  
- 🎛️ **Sounddevice** for voice recording  

---

## ✨ Features

- 🔗 **Natural Language → SQL** using a local/open-source LLM (llama3.1:8b) (via [Ollama](https://ollama.com))  
- 🎤 **Voice Input** (records from microphone, transcribed using OpenAI's Faster-Whisper)  
- 🗣️ **Voice Output** (speaks the response aloud)  
- 📊 **Dynamic Database Profiling** (tables + columns auto-injected into prompt)  
- 🧠 **Memory Support** (remembers last questions & answers for context / chit-chat)  
- 🛠️ **DB-Agnostic** (works with PostgreSQL, SQLite, or any SQLAlchemy-supported backend)  

---

## 📂 Project Structure

```
voice_to_sql-2/
│
├── app/
│   ├── __init__.py        # package init
│   ├── config.py          # settings loader (dotenv)
│   ├── db.py              # database connection
│   ├── prompts.py         # system & SQL planning prompts
│   ├── intent.py          # intent classification (SQL vs chitchat vs profile)
│   ├── memory.py          # simple memory (stores Q&A history)
│   ├── pipeline.py        # NL → SQL → execution pipeline
│   ├── profile.py         # DB profiling utilities
│
├── data/                  # audio files, temp output
├── whisper.cpp/           # optional (if you use whisper.cpp instead of faster-whisper)
├── main.py                # text REPL for NL2SQL
├── voice_app.py           # voice-based REPL (STT + SQL + TTS)
├── requirements.txt       # dependencies
└── README.md              # this file
```

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/voice_to_sql.git
cd voice_to_sql
```

### 2. Create environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install requirements

```bash
pip install -r requirements.txt
```

### 4. Setup `.env`

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+psycopg://user:password@hostname:5432/dbname
```

Examples:
- PostgreSQL: `postgresql+psycopg://user:pass@localhost:5432/mydb`
- SQLite: `sqlite:///mydb.sqlite`

### 5. Run the app

#### Text mode:

```bash
python main.py
```

#### Voice mode:

```bash
python voice_app.py
```

---

## ⚙️ Configuration

Environment variables (set in `.env` or export):

| Variable         | Default    | Description |
|------------------|------------|-------------|
| `DATABASE_URL`   | —          | SQLAlchemy connection string |
| `VOICE_SECONDS`  | 8          | Recording length in seconds |
| `VOICE_SR`       | 16000      | Audio sample rate |
| `VOICE_TTS`      | 1          | Enable text-to-speech (0 = off) |
| `FW_MODEL`       | large-v3   | Faster-Whisper model size (`tiny`, `base`, `small`, `medium`, `large-v3`) |
| `FW_DEVICE`      | cpu        | Device (`cpu` or `cuda`) |
| `FW_COMPUTE`     | int8       | Compute precision (`int8`, `int8_float32`, `float16`, `float32`) |

---

## 📖 Example Queries

- “**How many tables are in my database?**”  
- “**List the columns in the `users` table.**”  
- “**Show the first 10 rows of the `orders` table.**”  
- “**What’s my last question?**” (memory recall)  
- “**Tell me about the description column in the ChemicalComponent table.**”  

---

## 🧠 How it Works

1. **Intent Classification** – Decide if the query is:
   - SQL (data/schema)  
   - Profile (schema summary)  
   - Chit-chat / memory recall  

2. **Schema Injection** – Fetch `information_schema` tables + columns and pass them into the SQL generation prompt.  

3. **SQL Generation** – LLM (via Ollama) writes SQL for the question.  

4. **Execution** – Run SQL via SQLAlchemy, preview top rows.  

5. **Summarization** – LLM summarizes results into natural language.  

6. **Memory** – Question + answer stored for future conversational context.  

7. **Speech** – If in voice mode, STT transcribes and TTS speaks the result.  

---

## 📦 Requirements

Main dependencies:

```
sqlalchemy>=2.0.0
psycopg[binary]>=3.1
langchain>=0.3.1
langchain-community>=0.3.1
langchain-ollama>=0.1.0
ollama>=0.1.8
faster-whisper>=0.10.0
sounddevice>=0.4.6
pyttsx3>=2.90
numpy>=1.24.0
python-dotenv>=1.0.1
```

---

## 🛠️ Development

Optional tools for dev:

```bash
pip install black flake8 pytest
```

- `black .` → format code  
- `flake8 .` → lint  
- `pytest` → run tests (if added later)  

---

## 🌟 Future Improvements
  
- [ ] Add **Dockerfile** for portable deployment  
- [ ] Web UI with **Streamlit** (instead of CLI)  
- [ ] Multi-database switching at runtime  
- [ ] Richer **memory (vector store)** instead of simple text log  
- [ ] Support **charts/visualizations** for SQL results  

---

## 📜 License

MIT License. Free for personal & commercial use.  

---

## 🙌 Acknowledgements

- [LangChain](https://www.langchain.com/)  
- [Ollama](https://ollama.com)  
- [Faster-Whisper](https://github.com/guillaumekln/faster-whisper)  
- [SQLAlchemy](https://www.sqlalchemy.org/)  
