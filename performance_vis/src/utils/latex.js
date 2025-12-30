/**
 * LaTeX 渲染工具函数
 */

/**
 * 标准化 LaTeX 文本
 * @param {string} latexText - LaTeX 文本
 * @returns {string} 标准化后的文本
 */
export function normalizeLatex(latexText) {
  if (!latexText) return ''
  
  let normalized = String(latexText)
  let changed = true
  
  // 处理嵌套的 mathrm/text/mathit/mathbf
  while (changed) {
    const before = normalized
    normalized = normalized.replace(/\\mathrm\s*\{\s*\{\s*([^}]+)\s*\}\s*\}/g, '\\mathrm{$1}')
    normalized = normalized.replace(/\\text\s*\{\s*\{\s*([^}]+)\s*\}\s*\}/g, '\\text{$1}')
    normalized = normalized.replace(/\\mathit\s*\{\s*\{\s*([^}]+)\s*\}\s*\}/g, '\\mathit{$1}')
    normalized = normalized.replace(/\\mathbf\s*\{\s*\{\s*([^}]+)\s*\}\s*\}/g, '\\mathbf{$1}')
    changed = (before !== normalized)
  }
  
  // 处理数字之间的空格
  changed = true
  while (changed) {
    const before = normalized
    normalized = normalized.replace(/(\d)\s+(\d)/g, '$1$2')
    changed = (before !== normalized)
  }
  
  // 清理 mathrm/text/mathit/mathbf 内部空格
  normalized = normalized.replace(/\\mathrm\s*\{\s*([^}]+)\s*\}/g, (match, content) => {
    const cleaned = content.replace(/\s+/g, '')
    return `\\mathrm{${cleaned}}`
  })
  normalized = normalized.replace(/\\text\s*\{\s*([^}]+)\s*\}/g, (match, content) => {
    const cleaned = content.replace(/\s+/g, '')
    return `\\text{${cleaned}}`
  })
  normalized = normalized.replace(/\\mathit\s*\{\s*([^}]+)\s*\}/g, (match, content) => {
    const cleaned = content.replace(/\s+/g, '')
    return `\\mathit{${cleaned}}`
  })
  normalized = normalized.replace(/\\mathbf\s*\{\s*([^}]+)\s*\}/g, (match, content) => {
    const cleaned = content.replace(/\s+/g, '')
    return `\\mathbf{${cleaned}}`
  })
  
  // 处理上标和下标
  normalized = normalized.replace(/\^\s*\{\s*([^}]+)\s*\}/g, (match, content) => {
    const cleaned = content.replace(/\s+/g, '')
    return `^{${cleaned}}`
  })
  normalized = normalized.replace(/_\s*\{\s*([^}]+)\s*\}/g, (match, content) => {
    const cleaned = content.replace(/\s+/g, '')
    return `_{${cleaned}}`
  })
  
  // 合并连续的 mathrm
  normalized = normalized.replace(/\\mathrm\{([^}]+)\}\s*\\mathrm\{([^}]+)\}/g, '\\mathrm{$1}\\,\\mathrm{$2}')
  
  // 清理简单花括号内的空格
  normalized = normalized.replace(/\{\s*([a-zA-Z\s]+)\s*\}/g, (match, content) => {
    if (!content.includes('\\') && !content.includes('^') && !content.includes('_')) {
      const cleaned = content.replace(/\s+/g, '')
      return `{${cleaned}}`
    }
    return match
  })
  
  // 清理首尾的逗号和空格
  normalized = normalized.trim().replace(/^[,\s]+/, '').replace(/[,\s]+$/, '')
  
  return normalized
}

/**
 * 渲染 LaTeX 文本为 HTML
 * @param {string} text - 包含 LaTeX 的文本
 * @returns {string} HTML 字符串
 */
export function renderLatex(text) {
  if (!text) return ''
  
  let normalizedText = String(text)
  const dollarRegex = /\$([^$]+)\$/g
  let match
  const formulas = []
  let formulaIndex = 0
  const formulaPlaceholder = '___KATEX_FORMULA___'
  
  // 提取所有 $...$ 公式
  while ((match = dollarRegex.exec(text)) !== null) {
    const formulaContent = match[1]
    const normalizedFormula = normalizeLatex(formulaContent)
    formulas.push(`$${normalizedFormula}$`)
    normalizedText = normalizedText.replace(match[0], `${formulaPlaceholder}${formulaIndex}${formulaPlaceholder}`)
    formulaIndex++
  }
  
  // 处理包含反斜杠的文本
  if (normalizedText.includes('\\')) {
    const parts = normalizedText.split(new RegExp(`(${formulaPlaceholder}\\d+${formulaPlaceholder})`, 'g'))
    const processedParts = parts.map(part => {
      if (part.match(new RegExp(`${formulaPlaceholder}\\d+${formulaPlaceholder}`))) {
        return part
      }
      if (part.includes('\\')) {
        return normalizeLatex(part)
      }
      return part
    })
    normalizedText = processedParts.join('')
  }
  
  // HTML 转义
  const escapeHtml = (str) => {
    const div = document.createElement('div')
    div.textContent = str
    return div.innerHTML
  }
  
  let html = escapeHtml(normalizedText)
  
  // 恢复公式占位符
  formulas.forEach((formula, index) => {
    html = html.replace(`${formulaPlaceholder}${index}${formulaPlaceholder}`, formula)
  })
  
  return html
}

/**
 * 模糊高亮匹配
 * @param {string} rawText - 原始文本
 * @param {string} targetValue - 目标值
 * @param {number} windowBuffer - 窗口缓冲区大小
 * @param {number} highlightRange - 高亮范围
 * @returns {string} 高亮后的 HTML
 */
export function fuzzyHighlight(rawText, targetValue, windowBuffer = 15, highlightRange = 35) {
  const cleanTarget = String(targetValue).replace(/\s+/g, '')
  if (!cleanTarget || !rawText) return rawText || ''
  
  let bestStart = -1
  let bestEnd = -1
  
  // 搜索逻辑
  for (let i = 0; i < rawText.length; i++) {
    if (rawText[i] === cleanTarget[0]) {
      let matchCount = 0
      let tempIdx = i
      let matchedIndices = []
      
      for (let char of cleanTarget) {
        let found = false
        let searchLimit = tempIdx + windowBuffer
        
        while (tempIdx < rawText.length && tempIdx < searchLimit) {
          if (rawText[tempIdx] === char) {
            matchCount++
            matchedIndices.push(tempIdx)
            found = true
            tempIdx++
            break
          }
          tempIdx++
        }
        if (!found) break
      }
      
      if (matchCount === cleanTarget.length) {
        const charSpanStart = matchedIndices[0]
        const charSpanEnd = matchedIndices[matchedIndices.length - 1] + 1
        const matchCenter = Math.floor((charSpanStart + charSpanEnd) / 2)
        
        const half = Math.floor(highlightRange / 2)
        bestStart = Math.max(0, matchCenter - half)
        bestEnd = Math.min(rawText.length, matchCenter + (highlightRange - half))
        break
      }
    }
  }
  
  if (bestStart !== -1) {
    const before = rawText.substring(0, bestStart)
    const middle = rawText.substring(bestStart, bestEnd)
    const after = rawText.substring(bestEnd)
    
    return before + `<span style="background-color: #ff0000; color: white; font-weight: bold; padding: 0 2px;">${middle}</span>` + after
  }
  
  return rawText
}

/**
 * 提取文本中的可匹配字符序列（忽略 LaTeX 语法，但保留位置信息）
 * 关键：LaTeX 命令花括号内的内容仍然会被提取用于匹配
 * @param {string} text - 原始文本
 * @returns {Array<{char: string, origIndex: number}>} 字符序列和原始位置
 */
function extractMatchableChars(text) {
  const result = []
  let i = 0
  
  while (i < text.length) {
    const char = text[i]
    
    // 跳过 LaTeX 命令和语法字符，但提取花括号内的内容
    if (char === '\\') {
      const cmdStart = i
      i++ // 跳过反斜杠
      
      // 跳过命令名
      while (i < text.length && /[a-zA-Z]/.test(text[i])) {
        i++
      }
      
      // 跳过可能的空格
      while (i < text.length && /\s/.test(text[i])) {
        i++
      }
      
      // 如果后面是花括号，提取花括号内的内容用于匹配
      if (i < text.length && text[i] === '{') {
        i++ // 跳过开括号
        const braceStart = i
        let braceCount = 1
        
        // 找到匹配的闭括号
        while (i < text.length && braceCount > 0) {
          if (text[i] === '{') braceCount++
          else if (text[i] === '}') braceCount--
          i++
        }
        
        // 提取花括号内的内容（但不包括花括号本身）
        const braceContent = text.substring(braceStart, i - 1)
        // 递归处理花括号内容，提取其中的可匹配字符
        const innerChars = extractMatchableChars(braceContent)
        // 调整位置偏移
        innerChars.forEach(ic => {
          result.push({ char: ic.char, origIndex: braceStart + ic.origIndex })
        })
      }
    } else if (char === '$') {
      // 跳过 $...$ 或 $$...$$ 分隔符，但提取内容
      const isDouble = i + 1 < text.length && text[i + 1] === '$'
      const dollarStart = i
      i += isDouble ? 2 : 1
      const contentStart = i
      
      while (i < text.length) {
        if (text[i] === '$') {
          if (isDouble && i + 1 < text.length && text[i + 1] === '$') {
            // 提取 $...$ 内的内容
            const content = text.substring(contentStart, i)
            const innerChars = extractMatchableChars(content)
            innerChars.forEach(ic => {
              result.push({ char: ic.char, origIndex: contentStart + ic.origIndex })
            })
            i += 2
            break
          } else if (!isDouble) {
            const content = text.substring(contentStart, i)
            const innerChars = extractMatchableChars(content)
            innerChars.forEach(ic => {
              result.push({ char: ic.char, origIndex: contentStart + ic.origIndex })
            })
            i++
            break
          }
        }
        i++
      }
    } else if (char === '{' || char === '}') {
      // 跳过独立的花括号（这些通常不是 LaTeX 命令的一部分）
      i++
    } else if (char === '^' || char === '_') {
      // 处理上标下标：跳过标记，但提取内容
      const markStart = i
      i++ // 跳过 ^ 或 _
      
      if (i < text.length && text[i] === '{') {
        i++ // 跳过开括号
        const braceStart = i
        let braceCount = 1
        
        while (i < text.length && braceCount > 0) {
          if (text[i] === '{') braceCount++
          else if (text[i] === '}') braceCount--
          i++
        }
        
        // 提取花括号内的内容
        const braceContent = text.substring(braceStart, i - 1)
        const innerChars = extractMatchableChars(braceContent)
        innerChars.forEach(ic => {
          result.push({ char: ic.char, origIndex: braceStart + ic.origIndex })
        })
      } else if (i < text.length) {
        // 单个字符的上标/下标，仍然提取
        result.push({ char: text[i], origIndex: i })
        i++
      }
    } else {
      // 可匹配字符，记录
      result.push({ char, origIndex: i })
      i++
    }
  }
  
  return result
}

/**
 * 在原始文本中查找匹配位置（能识别 LaTeX 命令内的内容）
 * @param {string} originalText - 原始文本
 * @param {string} targetValue - 目标值
 * @returns {Array<{start: number, end: number}>} 匹配位置数组
 */
function findMatchesInOriginalText(originalText, targetValue) {
  const cleanTarget = String(targetValue).replace(/\s+/g, '')
  if (!cleanTarget || !originalText) return []
  
  // 提取可匹配字符序列
  const matchableChars = extractMatchableChars(originalText)
  if (matchableChars.length === 0) return []
  
  // 构建可匹配字符的字符串用于搜索
  const matchableText = matchableChars.map(m => m.char).join('')
  
  // 如果目标值太短或为空，直接返回
  if (cleanTarget.length === 0) return []
  
  let bestStart = -1
  let bestEnd = -1
  
  // 在可匹配字符序列中搜索（使用模糊匹配算法）
  for (let i = 0; i < matchableText.length; i++) {
    if (matchableText[i] === cleanTarget[0]) {
      let matchCount = 0
      let tempIdx = i
      let matchedIndices = []
      
      for (let char of cleanTarget) {
        let found = false
        let searchLimit = tempIdx + 15 // 窗口缓冲区
        
        while (tempIdx < matchableText.length && tempIdx < searchLimit) {
          if (matchableText[tempIdx] === char) {
            matchCount++
            matchedIndices.push(tempIdx)
            found = true
            tempIdx++
            break
          }
          tempIdx++
        }
        if (!found) break
      }
      
      // 如果完全匹配
      if (matchCount === cleanTarget.length) {
        const charSpanStart = matchedIndices[0]
        const charSpanEnd = matchedIndices[matchedIndices.length - 1] + 1
        const matchCenter = Math.floor((charSpanStart + charSpanEnd) / 2)
        
        const half = Math.floor(35 / 2)
        const matchableStart = Math.max(0, matchCenter - half)
        const matchableEnd = Math.min(matchableText.length, matchCenter + (35 - half))
        
        // 映射回原始文本位置
        if (matchableStart < matchableChars.length && matchableEnd > 0) {
          bestStart = matchableChars[matchableStart].origIndex
          // 确保 end 位置有效
          const endIdx = Math.min(matchableEnd - 1, matchableChars.length - 1)
          if (endIdx >= 0 && endIdx < matchableChars.length) {
            bestEnd = matchableChars[endIdx].origIndex + 1
            break
          }
        }
      }
    }
  }
  
  if (bestStart === -1 || bestEnd <= bestStart) return []
  
  return [{
    start: bestStart,
    end: bestEnd
  }]
}

/**
 * 检查位置是否在 $...$ 公式内
 * @param {string} text - 原始文本
 * @param {number} pos - 位置
 * @returns {Object|null} 如果在内，返回 {start, end, content}，否则返回 null
 */
function findFormulaAtPosition(text, pos) {
  const dollarRegex = /\$([^$]+)\$/g
  let match
  
  while ((match = dollarRegex.exec(text)) !== null) {
    const formulaStart = match.index
    const formulaEnd = match.index + match[0].length
    const formulaContent = match[1]
    
    if (pos >= formulaStart && pos < formulaEnd) {
      return {
        start: formulaStart,
        end: formulaEnd,
        content: formulaContent
      }
    }
  }
  
  return null
}

/**
 * 清洗 LaTeX 语法，转换为纯文本
 * @param {string} latexText - LaTeX 文本
 * @returns {string} 纯文本
 */
function cleanLatexToPlainText(latexText) {
  if (!latexText) return ''
  
  let cleaned = String(latexText)
  
  // 移除 $...$ 分隔符
  cleaned = cleaned.replace(/\$\$?([^$]+)\$\$?/g, '$1')
  
  // 移除 \[...\] 和 \(...\) 分隔符
  cleaned = cleaned.replace(/\\\[([^\]]+)\\\]/g, '$1')
  cleaned = cleaned.replace(/\\\(([^)]+)\\\)/g, '$1')
  
  // 将 \mathrm{...}, \text{...} 等转换为纯文本
  cleaned = cleaned.replace(/\\mathrm\s*\{([^}]+)\}/g, '$1')
  cleaned = cleaned.replace(/\\text\s*\{([^}]+)\}/g, '$1')
  cleaned = cleaned.replace(/\\mathit\s*\{([^}]+)\}/g, '$1')
  cleaned = cleaned.replace(/\\mathbf\s*\{([^}]+)\}/g, '$1')
  
  // 移除上标下标标记，保留内容
  cleaned = cleaned.replace(/\^\s*\{([^}]+)\}/g, '$1')
  cleaned = cleaned.replace(/_\s*\{([^}]+)\}/g, '$1')
  cleaned = cleaned.replace(/\^([a-zA-Z0-9])/g, '$1')
  cleaned = cleaned.replace(/_([a-zA-Z0-9])/g, '$1')
  
  // 移除其他 LaTeX 命令，保留内容
  cleaned = cleaned.replace(/\\[a-zA-Z]+\s*\{([^}]+)\}/g, '$1')
  cleaned = cleaned.replace(/\\[a-zA-Z]+/g, '')
  
  // 移除花括号
  cleaned = cleaned.replace(/\{([^}]+)\}/g, '$1')
  
  // 移除多余的反斜杠
  cleaned = cleaned.replace(/\\/g, '')
  
  // 规范化空格
  cleaned = cleaned.replace(/\s+/g, ' ').trim()
  
  return cleaned
}

/**
 * 渲染 LaTeX 并高亮值（激进方案：清洗所有 LaTeX，在纯文本中匹配）
 * @param {string} text - 文本
 * @param {string|string[]} valuesToHighlight - 要高亮的值
 * @returns {string} HTML 字符串
 */
export function renderLatexWithHighlight(text, valuesToHighlight) {
  if (!text) return ''
  
  if (!valuesToHighlight) {
    return renderLatex(text)
  }
  
  const values = Array.isArray(valuesToHighlight) ? valuesToHighlight : [valuesToHighlight]
  const validValues = values.filter(v => v !== null && v !== undefined && v !== '' && String(v).trim() !== '')
  
  if (validValues.length === 0) {
    return renderLatex(text)
  }
  
  // 激进方案：先清洗所有 LaTeX 语法，转换为纯文本
  const plainText = cleanLatexToPlainText(String(text))
  
  if (!plainText) {
    return renderLatex(text)
  }
  
  // 在纯文本中查找匹配
  const matches = []
  
  validValues.forEach(value => {
    const valueStr = String(value).trim()
    if (!valueStr) return
    
    // 使用简单的模糊匹配在纯文本中查找
    const cleanTarget = valueStr.replace(/\s+/g, '')
    if (!cleanTarget) return
    
    let bestStart = -1
    let bestEnd = -1
    
    for (let i = 0; i < plainText.length; i++) {
      if (plainText[i] === cleanTarget[0]) {
        let matchCount = 0
        let tempIdx = i
        let matchedIndices = []
        
        for (let char of cleanTarget) {
          let found = false
          let searchLimit = tempIdx + 15
          
          while (tempIdx < plainText.length && tempIdx < searchLimit) {
            if (plainText[tempIdx] === char) {
              matchCount++
              matchedIndices.push(tempIdx)
              found = true
              tempIdx++
              break
            }
            tempIdx++
          }
          if (!found) break
        }
        
        if (matchCount === cleanTarget.length) {
          const charSpanStart = matchedIndices[0]
          const charSpanEnd = matchedIndices[matchedIndices.length - 1] + 1
          const matchCenter = Math.floor((charSpanStart + charSpanEnd) / 2)
          
          const half = Math.floor(35 / 2)
          bestStart = Math.max(0, matchCenter - half)
          bestEnd = Math.min(plainText.length, matchCenter + (35 - half))
          break
        }
      }
    }
    
    if (bestStart !== -1 && bestEnd > bestStart) {
      matches.push({ start: bestStart, end: bestEnd })
    }
  })
  
  if (matches.length === 0) {
    // 没有匹配，返回清洗后的纯文本（HTML 转义）
    const escapeHtml = (str) => {
      const div = document.createElement('div')
      div.textContent = str
      return div.innerHTML
    }
    return escapeHtml(plainText)
  }
  
  // 合并重叠的匹配区间
  matches.sort((a, b) => a.start - b.start)
  const mergedMatches = []
  if (matches.length > 0) {
    let currentMatch = matches[0]
    
    for (let i = 1; i < matches.length; i++) {
      if (matches[i].start <= currentMatch.end) {
        currentMatch.end = Math.max(currentMatch.end, matches[i].end)
      } else {
        mergedMatches.push(currentMatch)
        currentMatch = matches[i]
      }
    }
    mergedMatches.push(currentMatch)
  }
  
  // 在纯文本中高亮匹配的部分
  let highlightedText = plainText
  for (let i = mergedMatches.length - 1; i >= 0; i--) {
    const match = mergedMatches[i]
    const before = highlightedText.substring(0, match.start)
    const matchText = highlightedText.substring(match.start, match.end)
    const after = highlightedText.substring(match.end)
    highlightedText = before + 
      '<span style="background-color: #ff0000; color: white; font-weight: bold; padding: 0 2px;">' + 
      matchText + 
      '</span>' + 
      after
  }
  
  // HTML 转义（高亮标记已经包含 HTML，所以只需要转义非高亮部分）
  const escapeHtml = (str) => {
    const div = document.createElement('div')
    div.textContent = str
    return div.innerHTML
  }
  
  // 分段转义，保留高亮 HTML
  let html = ''
  const highlightRegex = /<span style="background-color: #ff0000; color: white; font-weight: bold; padding: 0 2px;">([\s\S]*?)<\/span>/g
  let lastIndex = 0
  let match
  
  while ((match = highlightRegex.exec(highlightedText)) !== null) {
    // 转义高亮标记之前的部分
    html += escapeHtml(highlightedText.substring(lastIndex, match.index))
    // 保留高亮标记（已经是 HTML）
    html += match[0]
    lastIndex = match.index + match[0].length
  }
  // 转义剩余部分
  html += escapeHtml(highlightedText.substring(lastIndex))
  
  return html
}

/**
 * 在元素中渲染 LaTeX
 * @param {HTMLElement} element - 目标元素
 */
export function renderLatexInElement(element) {
  // 动态导入 renderMathInElement
  if (typeof window !== 'undefined' && window.renderMathInElement) {
    try {
      window.renderMathInElement(element, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
          { left: '\\[', right: '\\]', display: true },
          { left: '\\(', right: '\\)', display: false }
        ],
        throwOnError: false
      })
    } catch (e) {
      console.error('Error rendering LaTeX:', e)
    }
  } else {
    // 如果 KaTeX auto-render 还未加载，延迟执行
    setTimeout(() => renderLatexInElement(element), 100)
  }
}

