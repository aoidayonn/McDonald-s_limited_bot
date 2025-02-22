import logging
import telegram
from bs4 import BeautifulSoup
import requests
import os
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("TOKEN")  # 環境変数から取得
bot = telegram.Bot(TOKEN)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

menu_urls = {
    '1': ('https://www.mcdonalds.co.jp/menu/burger/', "バーガー"),
    '2': ('https://www.mcdonalds.co.jp/menu/set/', "セット"),
    '3': ('https://www.mcdonalds.co.jp/menu/side/', "サイドメニュー"),
    '4': ('https://www.mcdonalds.co.jp/menu/drink/', "ドリンク"),
    '5': ('https://www.mcdonalds.co.jp/menu/happyset/', "ハッピーセット"),
    '6': ('https://www.mcdonalds.co.jp/menu/morning/', "朝マック"),
    '7': ('https://www.mcdonalds.co.jp/menu/dinner/', "夜マック"),
    '8': ('https://www.mcdonalds.co.jp/menu/dessert/', "スイーツ"),
    '9': ('https://www.mcdonalds.co.jp/menu/barista/', "マックカフェ"),
}


def get_limited_items(url):
    """
    指定されたURLから、期間限定商品のリストを取得し、重複を排除して返す
    """
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "html.parser")

    limited_items = {}  # 商品名をキーにした辞書で重複排除

    # すべての商品リストを取得
    products = soup.select('.product-list-card')

    for product in products:
        # 期間限定バッジの有無を確認（hidden クラスが付いていないかチェック）
        limited_badge = product.select_one('img[alt="期間限定"]')
        limited_offer = product.get("data-time-limited-offer-started-at")

        if limited_badge and 'hidden' not in limited_badge.get('class', []) or limited_offer:
            # 商品名の取得
            name_tag = product.select_one('.product-list-card-name')
            name = name_tag.get_text(strip=True) if name_tag else "不明"

            # 画像URLの取得（data-src）
            img_tag = product.select_one('.product-list-card-img picture img[data-src]')
            img_url = img_tag.get("data-src") if img_tag else ""

            if img_url.startswith("/"):  # URLが相対パスの場合、完全URLに変換
                img_url = "https://www.mcdonalds.co.jp" + img_url

            # 価格の取得（期間限定メニューは特別な構造）
            price_tag = product.select_one('.product-list-card-price span.product-list-card-price-number')
            price = price_tag.get_text(strip=True) if price_tag else "不明"

            limited_items[name] = (img_url, price)  # 商品名をキーにして辞書に追加（重複を自動で排除）

    return list(limited_items.items())  # [(商品名, (画像URL, 価格)), ...]



async def start_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        rf"こんにちは {user.mention_html()}さん!""\n"
        "私はMcDonald's_information_botです。\n"
        "マクドナルドの期間限定メニューの情報をお届けします。\n"
        "知りたい期間限定メニューのジャンルを選んでください:\n"
        "1.バーガー\n2.セット\n3.サイドメニュー\n4.ドリンク\n"
        "5.ハッピーセット\n6.朝マック\n7.夜マック\n8.スイーツ\n9.マックカフェ",
        reply_markup=ForceReply(selective=True),
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("私はマクドナルドの期間限定のメニューの情報をお届けします。\n"
                                    "知りたい期間限定メニューのジャンルを指定すると指定されたジャンルの期間限定メニューをお答えします。\n"
                                    "ex.サイドメニューの情報が知りたい時:\n'3'と入力してください")


async def user_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_in = update.message.text.strip()
    if user_in in menu_urls:
        url, category = menu_urls[user_in]
        limited_items = get_limited_items(url)

        if not limited_items:
            await update.message.reply_text(f"現在発売中の期間限定{category}はありません。")
        else:
            await update.message.reply_text(f"現在発売中の期間限定{category}は以下の通りです:")
            for name, (img_url, price) in limited_items:  # 修正
                await update.message.reply_photo(photo=img_url, caption=f"{name}\n価格: {price}")
    else:
        await start_message(update, context)



def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start_message))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_input))
    application.run_polling()


if __name__ == "__main__":
    main()
