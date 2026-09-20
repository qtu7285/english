/**
 * Markdown & Status Tag Renderer Module
 */
import { stripHtmlAndEntities, escapeAttr, makeAudioButton, processLineForAudio } from './audio.js';

export function renderMarkdown(text) {
  if (!text) return "";

  // Tự động ẩn dòng [NEXT] hướng dẫn nhập số câu luyện trên Web UI (vì đã có Quick Chips bên dưới)
  let clean = text.replace(/(?:^|\n)\s*\[NEXT\]\s*Nhập số câu[^\n]*/gi, '');

  let html = clean
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Code blocks
  html = html.replace(/```([a-z]*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Convert explicit audio placeholders: [audio:Text] or [🔊:Text] or [speak:Text]
  html = html.replace(/\[(?:audio|speak|play|sound|🔊):\s*([^\]]+)\]/gi, (match, toSpeak) => {
    const c = stripHtmlAndEntities(toSpeak)
      .replace(/[*#`"“”]/g, "")
      .trim();
    if (!c) return "";
    const attr = escapeAttr(c);
    return `<button type="button" class="inline-audio-btn" data-text="${attr}" title="Phát âm: ${attr}">🔊</button>`;
  });

  // Bold & Italic
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  // Auto divider with centered label for "Ví dụ:" or "Example:"
  html = html.replace(/(?:^|\n)(?:---|\*\*\*|___)\s*\n+(?:[-*•]\s*)?(?:###?\s*)?(?:<strong>)?(?:Ví dụ|Example)(?::)?(?:<\/strong>)?(?::)?/gim,
    '\n<div class="bubble-divider-label"><span>Examples</span></div>\n');

  html = html.replace(/(?:^|\n)(?!<div class="bubble-divider-label">)(?:[-*•]\s*)?(?:###?\s*)?(?:<strong>)(Ví dụ|Example)(?::)?(?:<\/strong>)(?::)?/gim,
    '\n<div class="bubble-divider-label"><span>Examples</span></div>\n');
  html = html.replace(/(?:^|\n)(?!<div class="bubble-divider-label">)(?:[-*•]\s*)?(?:###?\s*)(Ví dụ|Example)(?::)?(?=\s*\n|$)/gim,
    '\n<div class="bubble-divider-label"><span>Examples</span></div>\n');

  // Horizontal rules
  html = html.replace(/^(?:---|\*\*\*|___)\s*$/gim, '<hr class="bubble-divider">');

  // Status Badges & Emojis
  html = html.replace(/\[EN\](?::)?/g, '<span class="badge badge-en" title="Tiếng Anh">🇬🇧</span>');
  html = html.replace(/\[VI\](?::)?/g, '<span class="badge badge-vi" title="Tiếng Việt">🇻🇳</span>');
  html = html.replace(/\[OK\]/g, '<span class="badge badge-ok" title="Chính xác">✅</span>');
  html = html.replace(/\[X\]/g, '<span class="badge badge-error" title="Chưa đúng">❌</span>');
  html = html.replace(/\[~\]/g, '<span class="badge badge-warn" title="Gần đúng">⚠️</span>');
  html = html.replace(/\[RETRY\]/g, '<span class="badge badge-warn" title="Thử lại">🔄</span>');
  html = html.replace(/\[SAVE\]/g, '<span class="badge badge-tool" title="Đã lưu">💾</span>');
  html = html.replace(/\[NEXT\]/g, '<span class="badge badge-next" title="Tiếp theo">⏩</span>');
  html = html.replace(/\[CONFIRM\]/g, '<span class="badge badge-confirm" title="Xác nhận">💬</span>');
  html = html.replace(/\[D1\]/g, '<span class="badge badge-diff badge-d1" title="Cơ bản">🟢 D1</span>');
  html = html.replace(/\[D2\]/g, '<span class="badge badge-diff badge-d2" title="Trung bình">🟡 D2</span>');
  html = html.replace(/\[D3\]/g, '<span class="badge badge-diff badge-d3" title="Nâng cao">🔴 D3</span>');

  // Place audio icon at the END of lines containing target words or example sentences
  const rawLines = html.split('\n');
  const processedLines = rawLines.map(line => processLineForAudio(line));
  html = processedLines.join('\n');

  // Newlines to breaks
  html = html.replace(/\n\n+/g, '</p><p>');
  html = html.replace(/\n/g, '<br>');

  html = `<p>${html}</p>`;
  html = html.replace(/<p>\s*(<hr[^>]*>)\s*<\/p>/gi, '$1');
  html = html.replace(/<p>\s*(<div class="bubble-divider-label">.*?<\/div>)\s*<\/p>/gi, '$1');
  html = html.replace(/<p>\s*<br\s*\/?>/gi, '<p>');
  html = html.replace(/<br\s*\/?>\s*<\/p>/gi, '</p>');
  html = html.replace(/<p>\s*<\/p>/g, '');

  return html;
}
