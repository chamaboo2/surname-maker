import html
import json
import uuid

import streamlit as st
from openai import OpenAI
from supabase import create_client


# ============================================================
# 基本設定
# ============================================================

st.set_page_config(
    page_title="名字メーカー AI",
    page_icon="🌸",
    layout="centered",
)

# SecretsにOPENAI_MODELを設定した場合はそちらを使います。
# 未設定なら gpt-5.6-luna を使います。
MODEL = (
    st.secrets["OPENAI_MODEL"]
    if "OPENAI_MODEL" in st.secrets
    else "gpt-5.6-luna"
)


# ============================================================
# デザイン
# ============================================================

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
    margin-bottom: 0.25rem;
}

/* タイトル下の説明文：テーマに追従しつつ、十分なコントラストを確保 */
.sub-title {
    text-align: center;
    color: var(--text-color);
    opacity: 0.82;
    margin-bottom: 2rem;
}

/* 名字タイプの説明ボックス：ライト/ダーク双方で読める配色 */
.mode-note {
    padding: 0.9rem 1rem;
    border-radius: 12px;
    background: rgba(88, 166, 255, 0.15);
    color: var(--text-color) !important;
    border: 1px solid rgba(88, 166, 255, 0.28);
    border-left: 4px solid #ff4b6e;
    font-weight: 600;
    line-height: 1.65;
    margin: 0.75rem 0 1rem 0;
}

/* モード選択をカード型にする */
div[role="radiogroup"] {
    display: grid !important;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.55rem;
    width: 100%;
}

div[role="radiogroup"] > label {
    width: 100%;
    margin: 0 !important;
    padding: 0.72rem 0.8rem !important;
    border-radius: 12px;
    border: 1px solid rgba(127, 127, 127, 0.30);
    background: rgba(127, 127, 127, 0.08);
    transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
}

div[role="radiogroup"] > label:hover {
    border-color: rgba(255, 75, 110, 0.65);
    background: rgba(255, 75, 110, 0.07);
}

div[role="radiogroup"] > label:has(input:checked) {
    border-color: #ff4b6e;
    background: rgba(255, 75, 110, 0.12);
    box-shadow: 0 0 0 2px rgba(255, 75, 110, 0.13);
    font-weight: 700;
}

/* スマホでは縦並びにして詰まりをなくす */
@media (max-width: 640px) {
    div[role="radiogroup"] {
        grid-template-columns: 1fr;
        gap: 0.45rem;
    }

    div[role="radiogroup"] > label {
        padding: 0.68rem 0.75rem !important;
    }
}

/* ボタン幅 */
div.stButton > button {
    width: 100%;
}

/* おすすめ度のプログレスバーを赤〜ピンク系に統一 */
div[data-testid="stProgress"] div[role="progressbar"] {
    background-color: rgba(255, 75, 110, 0.15) !important;
}

div[data-testid="stProgress"] div[role="progressbar"] > div {
    background: linear-gradient(90deg, #ff6b8a, #ff3f67) !important;
}

/* Streamlitのバージョン差に備えたフォールバック */
div[data-testid="stProgress"] > div > div > div > div {
    background: linear-gradient(90deg, #ff6b8a, #ff3f67) !important;
}

/* ダークモードでの説明ボックス補強 */
@media (prefers-color-scheme: dark) {
    .mode-note {
        background: rgba(88, 166, 255, 0.12);
        border-color: rgba(139, 190, 255, 0.28);
        color: var(--text-color) !important;
    }
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# APIクライアント
# ============================================================

@st.cache_resource
def openai_client():
    return OpenAI(
        api_key=st.secrets["OPENAI_API_KEY"]
    )


@st.cache_resource
def supabase_client():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )


def supabase_is_configured():
    return (
        "SUPABASE_URL" in st.secrets
        and "SUPABASE_KEY" in st.secrets
    )


# ============================================================
# セッション
# ============================================================

if "results" not in st.session_state:
    st.session_state.results = []

if "last_mode" not in st.session_state:
    st.session_state.last_mode = ""

if "favorites" not in st.session_state:
    st.session_state.favorites = []

if "visitor_id" not in st.session_state:
    st.session_state.visitor_id = str(
        uuid.uuid4()
    )


# ============================================================
# OpenAI 出力形式
# ============================================================

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "surname": {
                        "type": "string"
                    },
                    "reading": {
                        "type": "string"
                    },
                    "score": {
                        "type": "integer"
                    },
                    "catchphrase": {
                        "type": "string"
                    },
                    "reason": {
                        "type": "string"
                    },
                },
                "required": [
                    "surname",
                    "reading",
                    "score",
                    "catchphrase",
                    "reason",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": [
        "candidates"
    ],
    "additionalProperties": False,
}


# ============================================================
# AIへの指示
# ============================================================

def build_prompt(
    first_name,
    first_reading,
    mode_name
):
    reading_text = (
        first_reading
        if first_reading
        else "未入力"
    )

    common = f"""
あなたは日本語の「名字メーカー」です。

入力された下の名前に似合う
名字候補を5個つくってください。

【入力】

下の名前：
{first_name}

下の名前の読み：
{reading_text}

モード：
{mode_name}


【必ず守ること】

・候補は5個

・5候補はなるべく
  違った雰囲気にする

・surname は名字だけを書く

・reading は
  名字の読みをひらがなで書く

・score は
  下の名前との相性や
  モードへの適合度を含めた
  おすすめ度を0〜100で付ける

・catchphrase は
  短く印象的な日本語にする

・reason は
  2〜3文程度にする

・人を傷つける表現、
  差別的表現、
  露骨な性的表現は避ける
"""

    if mode_name == "美しい名字":
        return common + """

【美しい名字モード】

音の響き、
漢字の見た目、
下の名前と続けて読んだときの
まとまりを最重視してください。

現実の日本の名字として
自然に感じる候補を中心にしてください。

候補ごとに、

・上品
・透明感
・知的
・柔らかい
・凛とした

など、
少しずつ方向性を変えてください。
"""

    if mode_name == "姓名判断":
        return common + """

【姓名判断モード】

姓名判断には複数の流派があり、
画数の数え方や解釈が異なることを
前提にしてください。

未来や運勢を断定しないでください。

主に、

・漢字の縁起のよい印象
・名字と名前の音の安定感
・フルネームとしてのまとまり
・字面のバランス

から評価してください。

reasonでは、

「〜という印象があります」
「〜と考えやすい組み合わせです」

など、
参考情報として説明してください。
"""

    return common + """

【中二病名字モード】

中二病感を最大限にしてください。

見た瞬間に
少し笑ってしまうくらい
大げさでも構いません。

例えば、

・漆黒
・月
・零
・神
・天
・冥
・夜
・幻
・終
・皇

などの雰囲気を
自由に利用して構いません。

実在する名字に限定しません。

創作名字もOKです。

ただし、
単なる漢字の羅列にはせず、
名字として一応読める形にしてください。

catchphrase は
特に大げさで面白くしてください。
"""


# ============================================================
# 名字生成
# ============================================================

def generate_surnames(
    first_name,
    first_reading,
    mode_name
):
    response = (
        openai_client()
        .responses
        .create(
            model=MODEL,
            input=build_prompt(
                first_name,
                first_reading,
                mode_name,
            ),
            reasoning={
                "effort": "none"
            },
            text={
                "format": {
                    "type": "json_schema",
                    "name": "surname_candidates",
                    "strict": True,
                    "schema": RESULT_SCHEMA,
                }
            },
            max_output_tokens=2200,
            store=False,
        )
    )

    data = json.loads(
        response.output_text
    )

    candidates = data.get(
        "candidates",
        []
    )

    cleaned = []

    for item in candidates:
        surname = str(
            item.get(
                "surname",
                ""
            )
        ).strip()

        reading = str(
            item.get(
                "reading",
                ""
            )
        ).strip()

        catchphrase = str(
            item.get(
                "catchphrase",
                ""
            )
        ).strip()

        reason = str(
            item.get(
                "reason",
                ""
            )
        ).strip()

        try:
            score = int(
                item.get(
                    "score",
                    0
                )
            )
        except (
            TypeError,
            ValueError
        ):
            score = 0

        score = max(
            0,
            min(
                score,
                100
            )
        )

        if not surname:
            continue

        cleaned.append(
            {
                "surname": surname,
                "reading": reading,
                "full_name": f"{surname} {first_name}".strip(),
                "score": score,
                "catchphrase": catchphrase,
                "reason": reason,
                "is_liked": False,
                "is_favorite": False,
            }
        )

    return cleaned


# ============================================================
# Supabase
# ============================================================

def save_generated_results(
    first_name,
    first_reading,
    mode_name,
    results
):
    if not results:
        return results

    if not supabase_is_configured():
        return results

    records = []

    for item in results:
        records.append(
            {
                "visitor_id": st.session_state.visitor_id,
                "input_name": first_name,
                "input_reading": first_reading or None,
                "mode": mode_name,
                "surname": item.get(
                    "surname",
                    ""
                ),
                "surname_reading": item.get(
                    "reading"
                ) or None,
                "full_name": item.get(
                    "full_name",
                    ""
                ),
                "score": item.get(
                    "score"
                ),
                "catchphrase": item.get(
                    "catchphrase"
                ) or None,
                "reason": item.get(
                    "reason"
                ) or None,
                "is_favorite": False,
                "is_liked": False,
            }
        )

    try:
        response = (
            supabase_client()
            .table(
                "surname_records"
            )
            .insert(
                records
            )
            .execute()
        )

        saved_rows = (
            response.data
            or []
        )

        for index, item in enumerate(
            results
        ):
            if index < len(
                saved_rows
            ):
                item["db_id"] = (
                    saved_rows[index]
                    .get(
                        "id"
                    )
                )

        return results

    except Exception as e:
        st.warning(
            "名字は生成できましたが、"
            "履歴をSupabaseに保存できませんでした。"
        )

        st.caption(
            str(e)
        )

        return results


# ============================================================
# Supabaseのレコード更新
# ============================================================

def update_record(
    db_id,
    values
):
    if not db_id:
        return False

    if not supabase_is_configured():
        return False

    try:
        (
            supabase_client()
            .table(
                "surname_records"
            )
            .update(
                values
            )
            .eq(
                "id",
                db_id
            )
            .execute()
        )

        return True

    except Exception as e:
        st.warning(
            "Supabaseへの保存に失敗しました。"
        )

        st.caption(
            str(e)
        )

        return False


# ============================================================
# お気に入り
# ============================================================

def add_favorite(
    item
):
    db_id = item.get(
        "db_id"
    )

    already_saved = any(
        (
            fav.get(
                "db_id"
            ) == db_id
        )
        if db_id
        else (
            fav.get(
                "surname"
            )
            ==
            item.get(
                "surname"
            )
            and
            fav.get(
                "full_name"
            )
            ==
            item.get(
                "full_name"
            )
            and
            fav.get(
                "mode"
            )
            ==
            item.get(
                "mode"
            )
        )
        for fav
        in st.session_state.favorites
    )

    if not already_saved:
        favorite = dict(
            item
        )

        favorite[
            "is_favorite"
        ] = True

        st.session_state.favorites.append(
            favorite
        )

    item[
        "is_favorite"
    ] = True

    if db_id:
        update_record(
            db_id,
            {
                "is_favorite": True
            }
        )


def remove_favorite(
    index
):
    favorite = (
        st.session_state.favorites[
            index
        ]
    )

    db_id = favorite.get(
        "db_id"
    )

    if db_id:
        update_record(
            db_id,
            {
                "is_favorite": False
            }
        )

    st.session_state.favorites.pop(
        index
    )


# ============================================================
# タイトル
# ============================================================

st.markdown(
    '<div class="main-title">'
    '🌸 名字メーカー AI'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="sub-title">'
    '名前を入れるだけで、'
    'AIがあなたに似合う名字を考えます。'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# 入力
# ============================================================

first_name = st.text_input(
    "名前",
    placeholder="例：花子",
)


first_reading = st.text_input(
    "名前の読み（任意）",
    placeholder="例：はなこ",
)


st.markdown(
    "## どんな名字をつくる？"
)


mode_label = st.radio(
    "モード",
    [
        "🌸 美しい名字",
        "🔮 姓名判断",
        "⚔️ 中二病名字",
    ],
    horizontal=True,
    label_visibility="collapsed",
)


mode_name = {
    "🌸 美しい名字": "美しい名字",
    "🔮 姓名判断": "姓名判断",
    "⚔️ 中二病名字": "中二病名字",
}[mode_label]


mode_notes = {
    "美しい名字": (
        "音の響き、漢字の美しさ、"
        "フルネームとしてのまとまりを重視します。"
    ),
    "姓名判断": (
        "姓名判断的な縁起のよさやバランスを、"
        "娯楽・参考情報として提案します。"
    ),
    "中二病名字": (
        "大げさで強烈、"
        "中二病感満載の面白い名字を"
        "本気で考えます。"
    ),
}


st.markdown(
    f'<div class="mode-note">'
    f'{html.escape(mode_notes[mode_name])}'
    f'</div>',
    unsafe_allow_html=True,
)


# ============================================================
# 名字を生成
# ============================================================

if st.button(
    "✨ 名字をつくる",
    type="primary",
    use_container_width=True,
):
    if not first_name.strip():
        st.error(
            "名前を入力してください。"
        )

    else:
        with st.spinner(
            "名字を考えています……"
        ):
            try:
                results = generate_surnames(
                    first_name.strip(),
                    first_reading.strip(),
                    mode_name,
                )

                results = save_generated_results(
                    first_name.strip(),
                    first_reading.strip(),
                    mode_name,
                    results,
                )

                for item in results:
                    item[
                        "mode"
                    ] = mode_name

                st.session_state.results = (
                    results
                )

                st.session_state.last_mode = (
                    mode_name
                )

            except Exception as e:
                st.error(
                    "名字の生成中に"
                    "エラーが発生しました。"
                )

                st.caption(
                    str(e)
                )


# ============================================================
# 結果
# ============================================================

if st.session_state.results:
    st.divider()

    st.markdown(
        f"## "
        f"{st.session_state.last_mode} "
        f"の候補"
    )

    for index, item in enumerate(
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
            0
        )

        catchphrase = item.get(
            "catchphrase",
            ""
        )

        reason = item.get(
            "reason",
            ""
        )

        with st.container(
            border=True
        ):
            st.markdown(
                f"### {surname}"
            )

            if reading:
                st.caption(
                    reading
                )

            st.markdown(
                f"**{full_name}**"
            )

            st.markdown(
                f"おすすめ度 "
                f"**{score} / 100**"
            )

            st.progress(
                score / 100
            )

            if catchphrase:
                st.markdown(
                    f"**{catchphrase}**"
                )

            if reason:
                st.write(
                    reason
                )

            # ボタンの役割を明確化
            st.caption(
                "♡ いいね：好みとして記録（現在は次の生成には自動反映しません）"
                "　／　☆ 保存する：お気に入り一覧に残します"
            )

            col1, col2 = st.columns(
                2
            )

            # --------------------------------------------
            # いいね
            # --------------------------------------------

            with col1:
                liked = bool(
                    item.get(
                        "is_liked"
                    )
                )

                if st.button(
                    (
                        "♥ いいね済み"
                        if liked
                        else
                        "♡ いいね"
                    ),
                    key=(
                        f"like-"
                        f"{item.get('db_id', index)}-"
                        f"{index}"
                    ),
                    disabled=liked,
                    use_container_width=True,
                ):
                    item[
                        "is_liked"
                    ] = True

                    if item.get(
                        "db_id"
                    ):
                        update_record(
                            item[
                                "db_id"
                            ],
                            {
                                "is_liked": True
                            },
                        )

                    st.success(
                        "「いいね」を記録しました。"
                    )

            # --------------------------------------------
            # 保存
            # --------------------------------------------

            with col2:
                favorite = bool(
                    item.get(
                        "is_favorite"
                    )
                )

                if st.button(
                    (
                        "★ 保存済み"
                        if favorite
                        else
                        "☆ 保存する"
                    ),
                    key=(
                        f"favorite-"
                        f"{item.get('db_id', index)}-"
                        f"{index}"
                    ),
                    disabled=favorite,
                    use_container_width=True,
                ):
                    add_favorite(
                        item
                    )

                    st.success(
                        f"「{surname}」を保存しました。"
                    )


# ============================================================
# お気に入り一覧
# ============================================================

if st.session_state.favorites:
    st.divider()

    with st.expander(
        (
            "☆ 保存した名字"
            f"（{len(st.session_state.favorites)}件）"
        ),
        expanded=False,
    ):
        for index, favorite in enumerate(
            list(
                st.session_state.favorites
            )
        ):
            surname = favorite.get(
                "surname",
                ""
            )

            reading = favorite.get(
                "reading",
                ""
            )

            full_name = favorite.get(
                "full_name",
                ""
            )

            mode = favorite.get(
                "mode",
                ""
            )

            st.markdown(
                f"**{surname}**　"
                f"{reading}"
            )

            st.caption(
                f"{full_name} ／ "
                f"{mode}"
            )

            if st.button(
                "保存から外す",
                key=(
                    f"remove-favorite-"
                    f"{favorite.get('db_id', index)}-"
                    f"{index}"
                ),
            ):
                remove_favorite(
                    index
                )

                st.rerun()

            st.markdown(
                "---"
            )


# ============================================================
# 注意書き
# ============================================================

st.divider()

st.caption(
    "※ 姓名判断には複数の流派があり、"
    "漢字の画数の数え方や解釈も異なります。"
    "本アプリの姓名判断は"
    "娯楽・参考情報としてご利用ください。"
)


if not supabase_is_configured():
    st.caption(
        "※ Supabaseが未設定のため、"
        "生成履歴・評価データは"
        "永続保存されません。"
    )
