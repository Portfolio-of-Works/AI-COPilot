import { useState } from 'react'
import './App.css'

function App() {
  // State to store the chat history
  const [messages, setMessages] = useState([
    { role: 'assistant', text: '你好！我是智审 Co-pilot。请问有什么审计准则或实务问题我可以帮您解答？' }
  ]);
  
  // State to store the current text in the input box
  const [inputText, setInputText] = useState('');

  // Function to handle sending a message
  const handleSend = () => {
    if (inputText.trim() === '') return;

    // 1. Instantly display the user's message
    const newMessages = [...messages, { role: 'user', text: inputText }];
    setMessages(newMessages);
    setInputText('');

    // 2. Simulate the AI responding (Will connect to Python later)
    setTimeout(() => {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        text: '这是一个模拟回复。当后端连接后，这里将显示来自 Dialogflow 检索到的真实审计准则。' 
      }]);
    }, 1000);
  };

  // Allow sending by pressing the "Enter" key
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <div className="chat-container">
      {/* Chat History Area */}
      <div className="messages-area">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <strong>{msg.role === 'user' ? 'You: ' : '智审 Co-pilot: '}</strong>
            <br />
            {msg.text}
          </div>
        ))}
      </div>

      {/* Input Area */}
      <div className="input-area">
        <input 
          type="text" 
          className="chat-input"
          placeholder="例如：请解释新租赁准则下承租人会计处理..." 
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyPress}
        />
        <button className="send-button" onClick={handleSend}>
          发送
        </button>
      </div>
    </div>
  )
}

export default App
