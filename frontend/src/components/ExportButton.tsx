import React, { useState } from 'react'
import { Download, FileText, File } from 'lucide-react'
import html2pdf from 'html2pdf.js'

interface ExportButtonProps {
  data: any[]
  filename: string
  type: 'search-results' | 'conversation' | 'detail'
  className?: string
}

/**
 * Export button component for generating PDF/HTML/JSON exports
 */
function ExportButton({ data, filename, type, className = '' }: ExportButtonProps) {
  const [isExporting, setIsExporting] = useState(false)

  const exportToJSON = () => {
    const jsonString = JSON.stringify(data, null, 2)
    const blob = new Blob([jsonString], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${filename}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const exportToHTML = () => {
    let htmlContent = ''
    
    if (type === 'search-results') {
      htmlContent = generateSearchResultsHTML(data, filename)
    } else if (type === 'conversation') {
      htmlContent = generateConversationHTML(data, filename)
    } else if (type === 'detail') {
      htmlContent = generateDetailHTML(data, filename)
    }

    const blob = new Blob([htmlContent], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${filename}.html`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const exportToPDF = async () => {
    setIsExporting(true)
    
    try {
      let htmlContent = ''
      
      if (type === 'search-results') {
        htmlContent = generateSearchResultsHTML(data, filename)
      } else if (type === 'conversation') {
        htmlContent = generateConversationHTML(data, filename)
      } else if (type === 'detail') {
        htmlContent = generateDetailHTML(data, filename)
      }

      const element = document.createElement('div')
      element.innerHTML = htmlContent
      element.style.padding = '20px'

      const options = {
        margin: 1,
        filename: `${filename}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2 },
        jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
      }

      await html2pdf().set(options).from(element).save()
    } catch (error) {
      console.error('PDF export failed:', error)
      alert('Failed to export PDF. Please try again.')
    } finally {
      setIsExporting(false)
    }
  }

  const generateSearchResultsHTML = (results: any[], title: string) => {
    const timestamp = new Date().toLocaleString()
    
    return `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ForensiQ Search Results - ${title}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
        .result { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
        .result-meta { color: #666; font-size: 0.9em; margin-bottom: 10px; }
        .content { margin: 10px 0; line-height: 1.5; }
        .type-badge { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.8em; }
        .type-message { background: #e3f2fd; color: #1565c0; }
        .type-call { background: #e8f5e8; color: #2e7d32; }
        .type-contact { background: #f3e5f5; color: #7b1fa2; }
        .score { float: right; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <h1>ForensiQ Search Results</h1>
        <p><strong>Search Query:</strong> ${title.replace('forensiq-search-', '').replace(/-/g, ' ')}</p>
        <p><strong>Generated:</strong> ${timestamp}</p>
        <p><strong>Total Results:</strong> ${results.length}</p>
    </div>
    ${results.map((result, index) => `
        <div class="result">
            <div class="result-meta">
                <span class="type-badge type-${result.type}">${result.type}</span>
                <span class="score">Score: ${(result.score * 100).toFixed(1)}%</span>
                <br>
                ${result.contact ? `<strong>Contact:</strong> ${result.contact}<br>` : ''}
                ${result.phone ? `<strong>Phone:</strong> ${result.phone}<br>` : ''}
                ${result.timestamp ? `<strong>Date:</strong> ${new Date(result.timestamp).toLocaleString()}<br>` : ''}
                <strong>Source:</strong> ${result.source}
            </div>
            <div class="content">${result.content}</div>
        </div>
    `).join('')}
</body>
</html>`
  }

  const generateConversationHTML = (messages: any[], title: string) => {
    const timestamp = new Date().toLocaleString()
    
    return `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ForensiQ Conversation - ${title}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
        .message { margin: 10px 0; padding: 10px; border-radius: 10px; max-width: 70%; }
        .message.sent { background: #007bff; color: white; margin-left: auto; text-align: right; }
        .message.received { background: #f1f1f1; color: black; }
        .message-time { font-size: 0.8em; opacity: 0.7; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>ForensiQ Conversation</h1>
        <p><strong>Conversation:</strong> ${title}</p>
        <p><strong>Generated:</strong> ${timestamp}</p>
        <p><strong>Total Messages:</strong> ${messages.length}</p>
    </div>
    ${messages.map(message => `
        <div class="message ${message.direction || 'received'}">
            <div>${message.content || message.text}</div>
            <div class="message-time">${message.timestamp ? new Date(message.timestamp).toLocaleString() : 'Unknown time'}</div>
        </div>
    `).join('')}
</body>
</html>`
  }

  const generateDetailHTML = (details: any[], title: string) => {
    const timestamp = new Date().toLocaleString()
    
    return `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ForensiQ Evidence Detail - ${title}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
        .section { margin: 20px 0; }
        .section h2 { color: #333; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
        .metadata { background: #f9f9f9; padding: 15px; border-radius: 5px; }
        .metadata dt { font-weight: bold; margin-top: 10px; }
        .metadata dd { margin-left: 0; margin-bottom: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>ForensiQ Evidence Detail</h1>
        <p><strong>Evidence ID:</strong> ${title}</p>
        <p><strong>Generated:</strong> ${timestamp}</p>
    </div>
    ${details.map(item => `
        <div class="section">
            <h2>${item.title || 'Evidence Item'}</h2>
            <div class="metadata">
                <dl>
                    ${Object.entries(item).map(([key, value]) => `
                        <dt>${key}:</dt>
                        <dd>${value}</dd>
                    `).join('')}
                </dl>
            </div>
        </div>
    `).join('')}
</body>
</html>`
  }

  return (
    <div className={`inline-flex items-center space-x-2 ${className}`}>
      <span className="text-sm text-gray-600">Export:</span>
      
      <button
        onClick={exportToJSON}
        className="inline-flex items-center px-2 py-1 text-xs font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded hover:bg-gray-200 transition-colors"
        title="Export as JSON"
      >
        <File className="h-3 w-3 mr-1" />
        JSON
      </button>

      <button
        onClick={exportToHTML}
        className="inline-flex items-center px-2 py-1 text-xs font-medium text-blue-700 bg-blue-100 border border-blue-300 rounded hover:bg-blue-200 transition-colors"
        title="Export as HTML"
      >
        <FileText className="h-3 w-3 mr-1" />
        HTML
      </button>

      <button
        onClick={exportToPDF}
        disabled={isExporting}
        className="inline-flex items-center px-2 py-1 text-xs font-medium text-red-700 bg-red-100 border border-red-300 rounded hover:bg-red-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        title="Export as PDF"
      >
        <Download className="h-3 w-3 mr-1" />
        {isExporting ? 'Generating...' : 'PDF'}
      </button>
    </div>
  )
}

export default ExportButton