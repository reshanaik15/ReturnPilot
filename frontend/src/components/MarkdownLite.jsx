function renderInline(text, keyPrefix) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={`${keyPrefix}-${i}`}>{part.slice(2, -2)}</strong>;
    }
    return <span key={`${keyPrefix}-${i}`}>{part}</span>;
  });
}

// Minimal markdown support (bold + bullet lists) for agent responses.
// No HTML injection risk: text is only ever split into React text nodes, never dangerouslySetInnerHTML.
export default function MarkdownLite({ text }) {
  const lines = text.split('\n');
  const blocks = [];
  let currentList = null;

  lines.forEach((line, i) => {
    const bulletMatch = line.match(/^\s*[-*]\s+(.*)/);
    if (bulletMatch) {
      if (!currentList) {
        currentList = [];
        blocks.push(currentList);
      }
      currentList.push(bulletMatch[1]);
    } else {
      currentList = null;
      blocks.push(line);
    }
  });

  return (
    <>
      {blocks.map((block, i) => {
        if (Array.isArray(block)) {
          return (
            <ul key={i} className="list-disc list-inside my-1 space-y-0.5">
              {block.map((item, j) => (
                <li key={j}>{renderInline(item, `${i}-${j}`)}</li>
              ))}
            </ul>
          );
        }
        if (block === '') return <br key={i} />;
        return <p key={i}>{renderInline(block, `${i}`)}</p>;
      })}
    </>
  );
}
