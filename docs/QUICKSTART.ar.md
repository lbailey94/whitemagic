# البداية السريعة مع WhiteMagic

**اللغات:** [English](QUICKSTART.md) · [Español](QUICKSTART.es.md) · [Português (BR)](QUICKSTART.pt-BR.md) · [Français](QUICKSTART.fr.md) · [Deutsch](QUICKSTART.de.md) · [हिन्दी](QUICKSTART.hi.md) · [Indonesia](QUICKSTART.id.md) · **العربية** · [Kiswahili](QUICKSTART.sw.md) · [नेपाली](QUICKSTART.ne.md)

**الإصدار**: راجع الإصدار الحالي في [README](../README.md).
**مسار التثبيت**: Linux x86-64 وLinux arm64 وmacOS arm64 + x86_64
وWindows x86_64 — مسارات تثبيت موثّقة (install-gated). يوفّر Linux نسخ musl
ثابتة بالكامل يختارها المثبّت تلقائيًا (وتبقى نسخة مرتبطة ديناميكيًا متاحة
لأنظمة glibc 2.39+)؛ كما تنشر الإصدارات حزمًا مضغوطة gzip للاتصالات
البطيئة. يُثبَّت macOS عبر `install.sh`، وWindows عبر `install.ps1` —
ويُتحقق من كل مسار موثّق في CI مقابل الإصدار المنشور.

من الصفر إلى ذاكرة وكيل عاملة في أقل من خمس دقائق.

## مسار الثلاثين ثانية

```bash
wm grimoire          # أول تشغيل موجّه: المضيف، طبقة الذاكرة، الوكلاء، الذاكرة، المفردات، الاستمرارية
wm connect --write   # ربط كل عميل MCP مكتشف (جرّب أولًا: wm connect)
wm quickstart        # اختياري: عرض توضيحي للاستمرارية بين عمليتين على مخزن معزول
```

سترى قرارًا مشروعيًا سُجِّل في جلسة واحدة يصمد أمام إيقاف العملية وإعادة
تشغيلها بالكامل، ثم تستعيده الجلسة التالية. هذا هو المنتج.

## 1. التثبيت (بدون صلاحيات مدير)

### من إصدار جاهز

```bash
curl -fsSL https://www.whitemagic.dev/install.sh?ref=wmv9-quickstart | sh
```

على Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/lbailey94/whitemagic/main/scripts/install.ps1 | iex
```

يُنزِّل هذا أحدث إصدار، ويتحقق من بصمة SHA256 الخاصة به، ويثبّت `wm` في
`~/.local/bin` (على Windows: `%LOCALAPPDATA%\WhiteMagic\bin`، ويُضاف إلى
PATH الخاص بالمستخدم). إذا لم يكن هذا الدليل ضمن `PATH` لديك:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

البديل اليدوي: نزِّل ملفك التنفيذي حسب منصّتك (نسخ `wm-linux-x86_64-musl` /
`wm-linux-aarch64-musl` الثابتة، أو نسخ glibc 2.39+ وهي `wm-linux-x86_64` /
`wm-linux-aarch64`، أو `wm-macos-aarch64` / `wm-macos-x86_64`، أو
`wm-windows-x86_64.exe`؛ مع نسخة `.gz` حيث توفّرت وملف `.sha256` المرافق) من
[صفحة الإصدارات](https://github.com/lbailey94/whitemagic/releases)، ثم:

```bash
sha256sum -c wm-linux-x86_64.sha256
chmod +x wm-linux-x86_64
mkdir -p ~/.local/bin && mv wm-linux-x86_64 ~/.local/bin/wm
```

تتطلب النسخ المرتبطة ديناميكيًا glibc 2.39+ (بُنيت على Ubuntu 24.04)؛ أما
نسخ musl الثابتة فلا تتطلب glibc.

### من المصدر

يتطلب Rust 1.85+. بدون صلاحيات مدير:

```bash
cargo build --release
mkdir -p ~/.local/bin && cp target/release/wm ~/.local/bin/
```

## 2. التحقق والتفعيل

```bash
wm --version   # الإصدار الحالي
wm grimoire    # فحص أول موجّه؛ ينتهي بتسمية خطوة التفعيل
```

يثبت `wm grimoire` سلامة البيئة ويعرض معاينة لربط العملاء؛ أما التفعيل نفسه
فهو خطوة `wm connect --write` أدناه.

## 3. ربط عميل MCP

```bash
wm connect           # تشغيل تجريبي: العملاء المكتشفون والتغيير الدقيق
wm connect --write   # تعديل كل عميل مكتشف (مع نسخ احتياطية بطوابع زمنية أولًا)
```

أو اضبط عميلًا واحدًا صراحةً عبر `wm setup <client> [--write]`. الإعداد
اليدوي المكافئ:

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

## 4. اختياري: تشغيل عرض الاستمرارية

```bash
wm quickstart
```

يستخدم العرض مخزنًا معزولًا في `~/.local/share/whitemagic-quickstart` (لا
تُمَس بياناتك الحقيقية أبدًا). يعرض: بدء جلسة → تسجيل قرار → إيقاف العملية →
عملية جديدة → استعادة الاستمرارية للقرار → إعادة عرض بميزانية. احذفه في أي
وقت عبر `rm -rf ~/.local/share/whitemagic-quickstart`.

إذا بدا شيء غير سليم، فإن `wm doctor` هو أداة استكشاف الأخطاء (سلامة المخزن
والفهرس والسجل) — وليس خطوة إعداد.

يتحدث الخادم JSON-RPC عبر stdio ويعرض أداة ميتا واحدة `wm`. التوجيه الصريح
هو العقد الموثوق:

- `wm(route="session.continuity")` — استرجع الجلسة السابقة قبل بدء العمل
- `wm(route="session.start", args={"title": "..."})`
- `wm(route="session.record", args={"content": "...", "turn_type": "decision"})`
- `wm(route="tools.list")` — اكتشف كل ما تبقى

راجع [`MCP_CONFIG_GUIDE.md`](MCP_CONFIG_GUIDE.md) لإعداد كل عميل على حدة.

## 5. النسخ الاحتياطي

```bash
wm backup          # المخزن الكامل -> ~/whitemagic-backups/<timestamp>
wm restore --backup <dir> [--force]
```

احفظ النسخ الاحتياطية خارج الجهاز النشط. التفاصيل في README.
