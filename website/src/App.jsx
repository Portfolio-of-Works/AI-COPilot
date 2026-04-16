import { useState } from 'react'
import './App.css'

function App() {
  // Store the conversation history
  const [messages, setMessages] = useState([
    { sender: 'bot', text: '你好！我是智审 Co-pilot。请问有什么审计准则或实务问题我可以帮您解答？' }
  ])
  const [inputText, setInputText] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSendMessage = async (e) => {
    e.preventDefault()
    if (!inputText.trim()) return

    // 1. Add user's message to the screen immediately
    const userMessage = { sender: 'user', text: inputText }
    setMessages(prev => [...prev, userMessage])
    setInputText('')
    setIsLoading(true)

    try {
      // 2. THE HANDSHAKE: Send the message to your Python Backend
      const response = await fetch('https://ai-copilot-backend-1027738760886.us-west2.run.app/api/chat', { // https://ai-copilot-backend-1027738760886.us-west2.run.app/api/chat  http://127.0.0.1:8000/api/chat
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: userMessage.text })
      })

      if (!response.ok) {
        throw new Error('Network response was not ok')
      }

      const data = await response.json()

      // 3. Add the Python server's reply to the screen
      setMessages(prev => [...prev, { sender: 'bot', text: data.reply }])

    } catch (error) {
      console.error('Error connecting to backend:', error)
      setMessages(prev => [...prev, { sender: 'bot', text: '【连接错误】无法连接到本地服务器，请确保 Python 后端正在运行。' }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="chat-container">
      <header className="chat-header">
        <h1>智审 Co-pilot</h1>
      </header>
      
      <div className="chat-history">
        {messages.map((msg, index) => (
          <div key={index} className={`message-bubble ${msg.sender}`}>
            {msg.text}
          </div>
        ))}
        {isLoading && <div className="message-bubble bot">正在思考中...</div>}
      </div>

      <form className="chat-input-area" onSubmit={handleSendMessage}>
        <input 
          type="text" 
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="例如：请解释新租赁准则下承租人会计处理..." 
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading}>发送</button>
      </form>
    </div>
  )
}

export default App
