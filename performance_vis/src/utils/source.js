/**
 * Source 处理工具函数
 */

/**
 * 归一化 source 字段
 * @param {any} src - source 数据
 * @returns {string[]} 归一化后的字符串数组
 */
export function normalizeSource(src) {
  if (!src) return []
  
  // 如果是列表
  if (Array.isArray(src)) {
    return src.map(v => typeof v === 'string' ? v : JSON.stringify(v))
  }
  
  // 如果是对象且包含 table_source 或 reference_text_list
  if (typeof src === 'object') {
    const arr = []
    if (src.reference_text_list && Array.isArray(src.reference_text_list)) {
      arr.push(...src.reference_text_list)
    }
    if (src.table_source) {
      const t = src.table_source
      const loc = t.location ? `Table: ${t.location}` : 'Table source'
      arr.push(loc)
    }
    return arr
  }
  
  // 其他类型，转字符串
  return [String(src)]
}

/**
 * 判断是否为表格来源
 * @param {any} src - source 数据
 * @returns {boolean}
 */
export function isTableSource(src) {
  return src && typeof src === 'object' && !Array.isArray(src) && 
    (src.table_source || src.reference_text_list || src.source_content)
}

/**
 * 判断是否为图片来源
 * @param {any} src - source 数据
 * @returns {boolean}
 */
export function isFigureSource(src) {
  return src && typeof src === 'object' && src.img_path
}

/**
 * 获取表格引用文本列表
 * @param {any} src - source 数据
 * @returns {string[]}
 */
export function getTableRefs(src) {
  if (!src || typeof src !== 'object') return []
  if (src.table_source && Array.isArray(src.table_source.reference_text_list)) {
    return src.table_source.reference_text_list
  }
  if (Array.isArray(src.reference_text_list)) {
    return src.reference_text_list
  }
  return []
}

/**
 * 获取表格位置信息
 * @param {any} src - source 数据
 * @returns {string}
 */
export function getTableLocation(src) {
  if (!src || typeof src !== 'object') return ''
  if (src.table_source && src.table_source.location) {
    return src.table_source.location
  }
  return src.location || ''
}

/**
 * 获取表格 HTML 内容
 * @param {any} src - source 数据
 * @returns {string}
 */
export function getTableHtml(src) {
  if (!src || typeof src !== 'object') return ''
  if (src.table_source && src.table_source.source_content) {
    return src.table_source.source_content
  }
  return src.source_content || ''
}

/**
 * 获取图片引用文本列表
 * @param {any} fig - figure_source 数据
 * @returns {string[]}
 */
export function getFigureRefs(fig) {
  if (!fig || typeof fig !== 'object') return []
  if (Array.isArray(fig.reference_text_list)) {
    return fig.reference_text_list
  }
  return []
}

/**
 * 获取图片位置信息
 * @param {any} fig - figure_source 数据
 * @returns {string}
 */
export function getFigureLocation(fig) {
  if (!fig || typeof fig !== 'object') return ''
  return fig.location || ''
}

/**
 * 获取图片路径
 * @param {any} fig - figure_source 数据
 * @returns {string}
 */
export function getFigureImgPath(fig) {
  if (!fig || typeof fig !== 'object') return ''
  return fig.img_path || ''
}

/**
 * 获取证据类型统计
 * @param {any} alloy - alloy 数据对象
 * @returns {{text: number, table: number, figure: number}}
 */
export function getEvidenceSummary(alloy) {
  const acc = { text: 0, table: 0, figure: 0 }
  
  const visit = (node) => {
    if (!node) return
    
    if (Array.isArray(node)) {
      node.forEach(visit)
      return
    }
    
    if (typeof node === 'object') {
      if (node.figure_source && typeof node.figure_source === 'object') {
        acc.figure += 1
        visit(node.figure_source)
      }
      
      if (node.source !== undefined) {
        const s = node.source
        if (Array.isArray(s)) {
          acc.text += 1
        } else if (s && typeof s === 'object') {
          if (s.table_source || s.source_content) {
            acc.table += 1
          } else {
            acc.text += 1
          }
          visit(s)
        }
      }
      
      if (node.table_source) {
        acc.table += 1
      }
      
      Object.values(node).forEach(visit)
    }
  }
  
  visit(alloy)
  return acc
}

/**
 * 获取 source 数量
 * @param {any} src - source 数据
 * @returns {number}
 */
export function getSourceCount(src) {
  if (!src) return 0
  if (Array.isArray(src)) return src.length
  if (typeof src === 'object') {
    let count = 0
    if (src.reference_text_list && Array.isArray(src.reference_text_list)) {
      count += src.reference_text_list.length
    }
    if (src.table_source) count += 1
    return count
  }
  return 1
}

/**
 * 检查是否有任何 source
 * @param {any} src - source 数据
 * @returns {boolean}
 */
export function hasAnySource(src) {
  if (!src) return false
  if (Array.isArray(src)) return src.length > 0
  if (typeof src === 'object') {
    return !!(src.table_source || src.reference_text_list || src.source_content || src.img_path)
  }
  return true
}

