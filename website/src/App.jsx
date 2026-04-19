import { useState } from 'react'
import './App.css'

function App() {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: '你好！我是智审 Co-pilot。请问有什么审计准则或实务问题我可以帮您解答？' }
  ])
  const [inputText, setInputText] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSendMessage = async (e) => {
    e.preventDefault()
    if (!inputText.trim()) return

    const userMessageText = inputText;
    const userMessage = { sender: 'user', text: userMessageText }
    
    // Immediately show the user's message on screen
    setMessages(prev => [...prev, userMessage])
    setInputText('')
    setIsLoading(true)

    try {
      // ==========================================
      // STEP 1: The Fast Route (Query Dialogflow)
      // ==========================================
      const chatResponse = await fetch('https://copilot-backend-1027738760886.us-central1.run.app/api/chat', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: userMessageText })
      });

      if (!chatResponse.ok) throw new Error('Failed to connect to Dialogflow endpoint');
      const chatData = await chatResponse.json();

      // ==========================================
      // STEP 2: The Logic Fork
      // ==========================================
      if (chatData.reply.includes ('[TRIGGER_DEEP_SEARCH]')) {
        
        // Dialogflow failed to find it in the Data Store.
        // Create a temporary bot message to show we are pivoting to a deep search.
        setMessages(prev => [...prev, { sender: 'bot', text: '正在深度检索互联网资料...' }]);
        
        // ==========================================
        // STEP 3: The Slow/Stream Route (Vertex AI)
        // ==========================================
        const streamResponse = await fetch('https://copilot-backend-1027738760886.us-central1.run.app/api/stream-chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: userMessageText }) // We pass the same text to Engine B
        });

        if (!streamResponse.ok) throw new Error('Failed to connect to Streaming endpoint');

        // Hook into the data stream
        const reader = streamResponse.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let isFirstChunk = true;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');
          
          for (let line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.substring(6);
              
              if (dataStr === '[DONE]') {
                setIsLoading(false);
                break;
              }
              
              try {
                const parsed = JSON.parse(dataStr);
                if (parsed.error) throw new Error(parsed.error);
                
                setMessages(prev => {
                  const newMessages = [...prev];
                  // If this is the very first word, overwrite the "正在深度检索..." placeholder
                  if (isFirstChunk) {
                    newMessages[newMessages.length - 1].text = parsed.text;
                    isFirstChunk = false;
                  } else {
                    // Otherwise, append the new word to the running sentence
                    newMessages[newMessages.length - 1].text += parsed.text;
                  }
                  return newMessages;
                });
              } catch (err) {
                console.error('Error parsing stream chunk:', err);
              }
            }
          }
        }

      } else {
        // ==========================================
        // THE HAPPY PATH: Dialogflow found the answer!
        // ==========================================
        setMessages(prev => [...prev, { sender: 'bot', text: chatData.reply }]);
        setIsLoading(false);
      }

    } catch (error) {
      console.error('Error connecting to backend:', error)
      setMessages(prev => {
        const newMessages = [...prev]
        // If the error happens during streaming, we update the last message.
        // If it happens before, we add a new error message.
        if (newMessages[newMessages.length - 1].sender === 'bot') {
            newMessages[newMessages.length - 1].text = '【系统提示】网络连接异常或云端服务器响应失败，请稍后重试。'
        } else {
            newMessages.push({ sender: 'bot', text: '【系统提示】网络连接异常或云端服务器响应失败，请稍后重试。' })
        }
        return newMessages
      })
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
        {/* Only show the spinner if we are waiting for Dialogflow's initial response */}
        {isLoading && messages[messages.length-1].sender === 'user' && (
          <div className="message-bubble bot loading-indicator">正在检索知识库...</div>
        )}
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
