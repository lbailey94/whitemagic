# WhiteMagic द्रुत सुरुवात

**भाषाहरू:** [English](QUICKSTART.md) · [Español](QUICKSTART.es.md) · [Português (BR)](QUICKSTART.pt-BR.md) · [Français](QUICKSTART.fr.md) · [Deutsch](QUICKSTART.de.md) · [हिन्दी](QUICKSTART.hi.md) · [Indonesia](QUICKSTART.id.md) · [العربية](QUICKSTART.ar.md) · [Kiswahili](QUICKSTART.sw.md) · **नेपाली**

**संस्करण**: हालको संस्करण [README](../README.md) मा हेर्नुहोस्।
**स्थापना मार्ग**: Linux x86-64, Linux arm64, macOS arm64 + x86_64 र
Windows x86_64 — स्थापना-प्रमाणित (install-gated)। Linux ले पूर्ण स्ट्याटिक
musl बिल्ड दिन्छ, जुन स्थापकले स्वतः छान्छ (glibc 2.39+ भएका होस्टका लागि
डायनामिक बिल्ड पनि उपलब्ध रहन्छ); रिलिजहरूले ढिलो जडानका लागि gzip
संकुचित वितरण पनि प्रकाशित गर्छन्। macOS `install.sh` बाट स्थापना हुन्छ;
Windows `install.ps1` बाट — हरेक प्रमाणित मार्ग CI मा प्रकाशित रिलिजविरुद्ध
प्रमाणित गरिन्छ।

शून्यबाट काम गर्ने एजेन्ट मेमोरीसम्म पाँच मिनेटभन्दा कममा।

## ३०-सेकेन्ड मार्ग

```bash
wm grimoire          # निर्देशित पहिलो रन: होस्ट, मेमोरी तह, एजेन्ट, मेमोरी, शब्दावली, निरन्तरता
wm connect --write   # पहिचान भएको हरेक MCP क्लाइन्ट जोड्नुहोस् (पहिले परीक्षण: wm connect)
wm quickstart        # वैकल्पिक: अलग स्टोरमा दुई-प्रक्रिया निरन्तरता डेमो
```

एउटै सत्रमा अभिलेख गरिएको परियोजना निर्णय पूर्ण प्रक्रिया बन्द/पुनःसुरु हुँदा
पनि टिकिरहन्छ र अर्को सत्रले त्यसलाई पुनः प्राप्त गर्छ। त्यही नै उत्पादन हो।

## १. स्थापना (एडमिन अधिकार चाहिँदैन)

### रिलिजबाट

```bash
curl -fsSL https://www.whitemagic.dev/install.sh?ref=wmv9-quickstart | sh
```

Windows मा (PowerShell):

```powershell
irm https://raw.githubusercontent.com/lbailey94/whitemagic/main/scripts/install.ps1 | iex
```

यसले नवीनतम रिलिज डाउनलोड गर्छ, त्यसको SHA256 चेकसम प्रमाणित गर्छ, र `wm`
लाई `~/.local/bin` मा स्थापना गर्छ (Windows:
`%LOCALAPPDATA%\WhiteMagic\bin`, प्रयोगकर्ता PATH मा थपिन्छ)। यदि त्यो
डाइरेक्टरी तपाईंको `PATH` मा छैन भने:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

म्यानुअल विकल्प: आफ्नो प्लेटफर्मको बाइनरी डाउनलोड गर्नुहोस् (स्ट्याटिक
`wm-linux-x86_64-musl` / `wm-linux-aarch64-musl` बिल्ड, glibc 2.39+
`wm-linux-x86_64` / `wm-linux-aarch64` बिल्ड, `wm-macos-aarch64` /
`wm-macos-x86_64`, वा `wm-windows-x86_64.exe`; जहाँ उपलब्ध छ त्यहाँ `.gz`
संस्करण र `.sha256` फाइलसहित) [रिलिज पृष्ठ](https://github.com/lbailey94/whitemagic/releases)
बाट, त्यसपछि:

```bash
sha256sum -c wm-linux-x86_64.sha256
chmod +x wm-linux-x86_64
mkdir -p ~/.local/bin && mv wm-linux-x86_64 ~/.local/bin/wm
```

डायनामिक बिल्डका लागि glibc 2.39+ चाहिन्छ (Ubuntu 24.04 मा बनेको); स्ट्याटिक
musl बिल्डलाई glibc आवश्यक पर्दैन।

### स्रोतबाट

Rust 1.85+ चाहिन्छ। एडमिन अधिकार चाहिँदैन:

```bash
cargo build --release
mkdir -p ~/.local/bin && cp target/release/wm ~/.local/bin/
```

## २. प्रमाणित गर्नुहोस् र सक्रिय गर्नुहोस्

```bash
wm --version   # हालको संस्करण
wm grimoire    # निर्देशित पहिलो जाँच; अन्त्यमा सक्रियता चरण बताउँछ
```

`wm grimoire` ले वातावरण प्रमाणित गर्छ र क्लाइन्ट जडानको पूर्वावलोकन देखाउँछ;
सक्रियता आफैँ तलको `wm connect --write` चरण हो।

## ३. आफ्नो MCP क्लाइन्ट जोड्नुहोस्

```bash
wm connect           # ड्राई रन: पहिचान भएका क्लाइन्ट र ठ्याक्कै परिवर्तन
wm connect --write   # पहिचान भएको हरेक क्लाइन्ट प्याच गर्नुहोस् (पहिले टाइमस्ट्याम्प सहितका ब्याकअप)
```

वा एउटा क्लाइन्ट स्पष्ट रूपमा कन्फिगर गर्नुहोस्: `wm setup <client> [--write]`।
समतुल्य म्यानुअल कन्फिग:

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

## ४. वैकल्पिक: निरन्तरता डेमो चलाउनुहोस्

```bash
wm quickstart
```

डेमोले `~/.local/share/whitemagic-quickstart` मा अलग स्टोर प्रयोग गर्छ
(तपाईंको वास्तविक डेटा कहिल्यै छुइँदैन)। यसले देखाउँछ: सत्र सुरु → निर्णय
अभिलेख → प्रक्रिया बन्द → नयाँ प्रक्रिया → निरन्तरताले निर्णय पुनः प्राप्त
गर्छ → बजेट-आधारित रिप्ले। कहिल्यै पनि हटाउनुहोस्:
`rm -rf ~/.local/share/whitemagic-quickstart`.

केही बिग्रेको लाग्यो भने, `wm doctor` समस्या-समाधान उपकरण हो (स्टोर, इन्डेक्स
र रजिस्ट्री स्वास्थ्य) — यो सेटअप चरण होइन।

सर्भरले stdio मा JSON-RPC बोल्छ र एउटा `wm` मेटा-टुल प्रस्तुत गर्छ। स्पष्ट
रुटिङ विश्वसनीय सम्झौता हो:

- `wm(route="session.continuity")` — काम सुरु गर्नुअघि अघिल्लो सत्र सम्झनुहोस्
- `wm(route="session.start", args={"title": "..."})`
- `wm(route="session.record", args={"content": "...", "turn_type": "decision"})`
- `wm(route="tools.list")` — बाँकी सबै पत्ता लगाउनुहोस्

क्लाइन्ट-विशिष्ट सेटअपका लागि [`MCP_CONFIG_GUIDE.md`](MCP_CONFIG_GUIDE.md)
हेर्नुहोस्।

## ५. ब्याकअप

```bash
wm backup          # पूरा स्टोर -> ~/whitemagic-backups/<timestamp>
wm restore --backup <dir> [--force]
```

ब्याकअप सक्रिय मेसिनबाहिर राख्नुहोस्। विवरण README मा।
