import streamlit as st
from openai import OpenAI
from supabase import create_client
import json
import re


# =========================================================
# 基本設定
# =========================================================

st.set_page_config(
    page_title="名字メーカー AI",
    page_icon="🌸",
    layout="centered",
)

@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )

supabase = get_supabase()

# =========================================================
# デザイン
# =========================================================

st.markdown(
    """
    <style>
    .block-container {
        max-width: 900px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    .main-title {
        text-align: center;
        font-size: 2.3rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }

    .sub-title {
        text-align: center;
        color: #777;
        margin-bottom: 2rem;
    }

    .name-box {
        border: 1px solid #dddddd;
        border-radius: 18px;
        padding: 20px;
        margin-bottom: 16px;
        background: #ffffff;
        box-shadow: 0 3px 12px rgba(0,0,0,0.05);
    }

    .surname {
        font-size: 1.7rem;
        font-weight: 800;
        margin-bottom: 3px;
    }

    .reading {
        color: #777777;
        font-size: 0.95rem;
    }

    .full-name {
        font-size: 1.25rem;
        font-weight: 700;
        margin-top: 12px;
        margin-bottom: 10px;
    }

    .score {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        background: #f3f3f3;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .small-note {
        color: #888888;
        font-size: 0.85rem;
    }

    div.stButton > button {
        border-radius: 12px;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# API
# =========================================================

def get_client():
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        return None

    return OpenAI(api_key=api_key)


client = get_client()


# =========================================================
# JSON整形
# =========================================================

def extract_json(text):
    text = text.strip()

    text = re.sub(r"^```json", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```", "", text)
    text = re.sub(r"```$", "", text)

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("JSONが見つかりませんでした。")

    return json.loads(text[start:end + 1])


# =========================================================
# プロンプト
# =========================================================

def make_prompt(first_name, first_reading, mode):

    reading_text = (
        first_reading
        if first_reading
        else "読みは入力されていません。一般的な読みを推定してください。"
    )

    common_rule = f"""
あなたは、日本語の名前に非常に詳しいネーミング専門家です。

下の名前：
{first_name}

下の名前の読み：
{reading_text}

この名前に合う「名字」を6個考えてください。

必ず、名字を付けたフルネームとして評価してください。

出力は必ず次のJSON形式だけにしてください。

{{
  "candidates": [
    {{
      "surname": "名字",
      "reading": "名字のひらがなの読み",
      "full_name": "名字 名前",
      "score": 95,
      "catchphrase": "短い一言",
      "reason": "理由"
    }}
  ]
}}

scoreは100点満点です。

同じ名字や、ほとんど同じ名字を繰り返さないでください。
"""

    if mode == "美しい名字":
        rule = """
【今回のテーマ：音や字がきれいな名字】

以下を特に重視してください。

・名字と名前を続けて読んだときの音の流れ
・母音や子音の響き
・漢字同士の見た目
・名字と名前から受ける全体的な印象
・日本人の名前として自然であること
・上品さ
・覚えやすさ

奇抜さよりも、美しさと自然さを優先してください。

reasonでは、
「音」
「漢字」
「フルネーム全体の印象」
のうち特に優れている点を具体的に説明してください。
"""

    elif mode == "姓名判断":
        rule = """
【今回のテーマ：姓名判断的に良さそうな名字】

日本で一般的に知られている姓名判断・五格
（天格・人格・地格・外格・総格）
の考え方を参考にしてください。

ただし姓名判断には複数の流派があり、
旧字体・新字体などによって画数が異なる場合があります。

そのため断定はせず、
「一般的な姓名判断を参考にした候補」
として名字を考えてください。

できるだけ、

・人格
・総格
・天地のバランス
・名字と名前の画数バランス

などを総合的に考えてください。

reasonでは、
なぜ姓名判断上よさそうなのかを簡潔に説明してください。

実在する、または日本の名字として十分自然な名字を優先してください。
"""

    else:
        rule = """
【今回のテーマ：中二病感満載の名字】

今回は真面目になりすぎないでください。

「漫画の最強キャラクター」
「封印された一族」
「古代から続く名家」
「何か特殊能力を持っていそう」
と思わせる名字を考えてください。

実在する名字である必要はありません。

・闇
・月
・皇
・神
・龍
・黒
・白
・天
・零
・影
・夜
・星
・帝
などの漢字を使っても構いませんが、
毎回同じパターンにはしないでください。

読み方も格好よくしてください。

ただし、名字として読める形にはしてください。

catchphraseには、
その人物の「一族設定」や「二つ名」を
短く面白く書いてください。

reasonは真面目な解説ではなく、
なぜ中二病的に強そうなのかを
少し笑える文章で説明してください。

遠慮せず、かなり振り切ってください。
"""

    return common_rule + rule


# =========================================================
# AI生成
# =========================================================

def generate_surnames(first_name, first_reading, mode):

    if client is None:
        raise RuntimeError(
            "OPENAI_API_KEY が設定されていません。"
        )

    model = st.secrets.get(
        "OPENAI_MODEL",
        "gpt-4.1-mini"
    )

    response = client.responses.create(
        model=model,
        input=make_prompt(
            first_name,
            first_reading,
            mode
        )
    )

    data = extract_json(response.output_text)

    return data.get("candidates", [])


# =========================================================
# セッション
# =========================================================

if "results" not in st.session_state:
    st.session_state.results = []

if "last_mode" not in st.session_state:
    st.session_state.last_mode = ""

if "favorites" not in st.session_state:
    st.session_state.favorites = []


# =========================================================
# タイトル
# =========================================================

st.markdown(
    '<div class="main-title">🌸 名字メーカー AI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">'
    '名前を入れるだけで、AIがあなたに似合う名字を考えます。'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# 名前入力
# =========================================================

first_name = st.text_input(
    "名前",
    placeholder="例：花子"
)

first_reading = st.text_input(
    "名前の読み（任意）",
    placeholder="例：はなこ"
)


# =========================================================
# モード
# =========================================================

st.markdown("### どんな名字をつくる？")

mode = st.radio(
    "モード",
    [
        "🌸 美しい名字",
        "🔮 姓名判断",
        "⚔️ 中二病名字"
    ],
    horizontal=True,
    label_visibility="collapsed"
)

mode_name = (
    mode
    .replace("🌸 ", "")
    .replace("🔮 ", "")
    .replace("⚔️ ", "")
)


# =========================================================
# モード説明
# =========================================================

if mode_name == "美しい名字":
    st.info(
        "音の響き、漢字の美しさ、"
        "フルネームとしてのまとまりを重視します。"
    )

elif mode_name == "姓名判断":
    st.info(
        "一般的な姓名判断・五格の考え方を参考に、"
        "相性のよさそうな名字を考えます。"
    )

else:
    st.info(
        "最強キャラ・封印された一族・伝説の名家。"
        "AIが遠慮せず考えます。"
    )


# =========================================================
# 生成ボタン
# =========================================================

generate_button = st.button(
    "✨ 名字をつくる",
    type="primary",
    use_container_width=True
)


if generate_button:

    if not first_name.strip():

        st.warning("名前を入力してください。")

    elif client is None:

        st.error(
            "OpenAI APIキーがまだ設定されていません。"
            "後で設定します。"
        )

    else:

        with st.spinner("名字を考えています……"):

            try:

                results = generate_surnames(
                    first_name.strip(),
                    first_reading.strip(),
                    mode_name
                )

                st.session_state.results = results
                st.session_state.last_mode = mode_name

            except Exception as e:

                st.error(
                    "名字の生成中にエラーが発生しました。"
                )

                st.caption(str(e))


# =========================================================
# 結果
# =========================================================

if st.session_state.results:

    st.markdown("---")

    st.markdown(
        f"## {st.session_state.last_mode} の候補"
    )

    for i, item in enumerate(
        st.session_state.results
    ):

        surname = item.get(
            "surname",
            ""
        )

        reading = item.get(
            "reading",
            ""
        )

        full_name = item.get(
            "full_name",
            ""
        )

        score = item.get(
            "score",
            ""
        )

        catchphrase = item.get(
            "catchphrase",
            ""
        )

        reason = item.get(
            "reason",
            ""
        )

        st.markdown(
            f"""
<div class="name-box">
<div class="surname">
{surname}
</div>

<div class="reading">
{reading}
</div>

<div class="full-name">
{full_name}
</div>

<div class="score">
おすすめ度 {score} / 100
</div>

<p>
<b>{catchphrase}</b>
</p>

<p>
{reason}
</p>

</div>
""",
            unsafe_allow_html=True
        )

        if st.button(
            "♡ この名字が好き",
            key=f"fav_{i}"
        ):

            favorite = {
                "surname": surname,
                "reading": reading,
                "full_name": full_name,
                "mode": st.session_state.last_mode
            }

            if favorite not in st.session_state.favorites:

                st.session_state.favorites.append(
                    favorite
                )

            st.success(
                f"「{surname}」をお気に入りにしました。"
            )


# =========================================================
# お気に入り
# =========================================================

if st.session_state.favorites:

    st.markdown("---")

    with st.expander(
        f"♡ お気に入り "
        f"（{len(st.session_state.favorites)}件）"
    ):

        for fav in st.session_state.favorites:

            st.write(
                f"**{fav['full_name']}**"
                f"（{fav['reading']}）"
                f"｜{fav['mode']}"
            )

        if st.button(
            "お気に入りを全部消す"
        ):

            st.session_state.favorites = []

            st.rerun()


# =========================================================
# 注意事項
# =========================================================

st.markdown("---")

st.caption(
    "※ 姓名判断には複数の流派があり、"
    "漢字の画数の数え方も異なります。"
    "本アプリの姓名判断は娯楽・参考情報としてご利用ください。"
)
