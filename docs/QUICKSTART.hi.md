# WhiteMagic क्विकस्टार्ट

**भाषाएँ:** [English](QUICKSTART.md) · [Español](QUICKSTART.es.md) · [Português (BR)](QUICKSTART.pt-BR.md) · [Français](QUICKSTART.fr.md) · [Deutsch](QUICKSTART.de.md) · **हिन्दी** · [Indonesia](QUICKSTART.id.md) · [العربية](QUICKSTART.ar.md) · [Kiswahili](QUICKSTART.sw.md) · [नेपाली](QUICKSTART.ne.md)

**संस्करण**: वर्तमान संस्करण [README](../README.md) में देखें।
**इंस्टॉल पथ**: Linux x86-64, Linux arm64, macOS arm64 + x86_64 और
Windows x86_64 — इंस्टॉल-गेटेड। Linux पूरी तरह स्टैटिक musl बिल्ड देता है,
जिन्हें इंस्टॉलर स्वतः चुनता है (glibc 2.39+ वाले होस्ट के लिए डायनामिक बिल्ड
भी उपलब्ध रहता है); रिलीज़ धीमे लिंक के लिए gzip संकुचित डिस्ट्रिब्यूशन भी
प्रकाशित करती हैं। macOS `install.sh` से इंस्टॉल होता है; Windows
`install.ps1` से — हर गेटेड पथ को CI में प्रकाशित रिलीज़ के विरुद्ध
प्रमाणित किया जाता है।

शून्य से पाँच मिनट से कम में काम करती एजेंट मेमोरी तक।

## 30-सेकंड पथ

```bash
wm grimoire          # निर्देशित पहला रन: होस्ट, मेमोरी परत, एजेंट, मेमोरी, शब्दावली, निरंतरता
wm connect --write   # पहचाने गए हर MCP क्लाइंट को जोड़ें (पहले परीक्षण: wm connect)
wm quickstart        # वैकल्पिक: अलग स्टोर पर दो-प्रक्रिया निरंतरता डेमो
```

आप देखेंगे कि एक सत्र में दर्ज परियोजना निर्णय पूर्ण प्रक्रिया बंद/प्रारंभ
के बाद भी बचा रहता है और अगला सत्र उसे पुनः प्राप्त कर लेता है। यही उत्पाद है।

## 1. इंस्टॉल करें (एडमिन अधिकार आवश्यक नहीं)

### रिलीज़ से

```bash
curl -fsSL https://www.whitemagic.dev/install.sh?ref=wmv9-quickstart | sh
```

Windows पर (PowerShell):

```powershell
irm https://raw.githubusercontent.com/lbailey94/whitemagic/main/scripts/install.ps1 | iex
```

यह नवीनतम रिलीज़ डाउनलोड करता है, उसका SHA256 चेकसम सत्यापित करता है, और
`wm` को `~/.local/bin` में इंस्टॉल करता है (Windows:
`%LOCALAPPDATA%\WhiteMagic\bin`, उपयोगकर्ता PATH में जोड़ा जाता है)। यदि वह
डायरेक्टरी आपके `PATH` में नहीं है:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

मैनुअल विकल्प: अपने प्लेटफ़ॉर्म का बाइनरी डाउनलोड करें (स्टैटिक
`wm-linux-x86_64-musl` / `wm-linux-aarch64-musl` बिल्ड, glibc 2.39+
`wm-linux-x86_64` / `wm-linux-aarch64` बिल्ड, `wm-macos-aarch64` /
`wm-macos-x86_64`, या `wm-windows-x86_64.exe`; जहाँ उपलब्ध हो वहाँ `.gz`
वेरिएंट और `.sha256` साइडकार सहित) [रिलीज़ पृष्ठ](https://github.com/lbailey94/whitemagic/releases)
से, फिर:

```bash
sha256sum -c wm-linux-x86_64.sha256
chmod +x wm-linux-x86_64
mkdir -p ~/.local/bin && mv wm-linux-x86_64 ~/.local/bin/wm
```

डायनामिक बिल्ड के लिए glibc 2.39+ आवश्यक है (Ubuntu 24.04 पर बने); स्टैटिक
musl बिल्ड के लिए glibc की आवश्यकता नहीं है।

### सोर्स से

Rust 1.85+ आवश्यक। एडमिन अधिकार आवश्यक नहीं:

```bash
cargo build --release
mkdir -p ~/.local/bin && cp target/release/wm ~/.local/bin/
```

## 2. सत्यापित करें और सक्रिय करें

```bash
wm --version   # वर्तमान संस्करण
wm grimoire    # निर्देशित पहला जाँच; अंत में सक्रियण चरण बताता है
```

`wm grimoire` वातावरण प्रमाणित करता है और क्लाइंट वायरिंग का पूर्वावलोकन
दिखाता है; सक्रियण स्वयं नीचे दिया गया `wm connect --write` चरण है।

## 3. अपना MCP क्लाइंट जोड़ें

```bash
wm connect           # ड्राई रन: पहचाने गए क्लाइंट और ठीक-ठीक बदलाव की सूची
wm connect --write   # पहचाने गए हर क्लाइंट को पैच करें (पहले टाइमस्टैम्प वाले बैकअप)
```

या किसी एक क्लाइंट को स्पष्ट रूप से कॉन्फ़िगर करें: `wm setup <client> [--write]`।
समतुल्य मैनुअल कॉन्फ़िग:

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "wm",
      "args": ["serve", "--profile", "curated"]
    }
  }
}
```

## 4. वैकल्पिक: निरंतरता डेमो चलाएँ

```bash
wm quickstart
```

डेमो `~/.local/share/whitemagic-quickstart` पर अलग स्टोर का उपयोग करता है
(आपका वास्तविक डेटा कभी छुआ नहीं जाता)। यह दिखाता है: सत्र प्रारंभ → निर्णय
दर्ज करें → प्रक्रिया बंद → नई प्रक्रिया → निरंतरता निर्णय पुनः प्राप्त
करती है → बजट-आधारित रीप्ले। कभी भी हटाएँ:
`rm -rf ~/.local/share/whitemagic-quickstart`.

यदि कुछ गड़बड़ लगे, तो `wm doctor` समस्या-निवारण उपकरण है (स्टोर, इंडेक्स
और रजिस्ट्री स्वास्थ्य) — यह सेटअप चरण नहीं है।

सर्वर stdio पर JSON-RPC बोलता है और एक `wm` मेटा-टूल प्रस्तुत करता है।
स्पष्ट रूटिंग विश्वसनीय अनुबंध है:

- `wm(route="session.continuity")` — काम शुरू करने से पहले पिछला सत्र याद करें
- `wm(route="session.start", args={"title": "..."})`
- `wm(route="session.record", args={"content": "...", "turn_type": "decision"})`
- `wm(route="tools.list")` — बाकी सब खोजें

क्लाइंट-विशिष्ट सेटअप के लिए [`MCP_CONFIG_GUIDE.md`](MCP_CONFIG_GUIDE.md)
देखें।

## 5. बैकअप

```bash
wm backup          # पूरा स्टोर -> ~/whitemagic-backups/<timestamp>
wm restore --backup <dir> [--force]
```

बैकअप लाइव मशीन से बाहर रखें। विवरण README में।
