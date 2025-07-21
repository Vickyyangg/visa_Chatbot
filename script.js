const chat = document.getElementById('chat');
const form = document.getElementById('inputForm');
const input = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const clearBtn = document.getElementById('clearBtn');

const messages = JSON.parse(localStorage.getItem('chatMessages') || '[]');

function formatTime() {
  const now = new Date();
  return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function addMessage(text, sender, save = true, prependIntro = false) {
  const div = document.createElement('div');
  div.classList.add('message', sender);

  if (sender === 'bot' && prependIntro) {
    const intro = document.createElement('div');
    intro.style.fontSize = '0.85rem';
    intro.style.fontStyle = 'italic';
    intro.style.marginBottom = '6px';
    intro.style.color = '#888';
    intro.textContent = "This is Vicky from Issa";
    div.appendChild(intro);
  }

  const messageText = document.createElement('div');
  messageText.textContent = text;

  const timestamp = document.createElement('div');
  timestamp.classList.add('timestamp');
  timestamp.textContent = formatTime();

  div.appendChild(messageText);
  div.appendChild(timestamp);

  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;

  if (save) {
    messages.push({ sender, text, time: Date.now() });
    localStorage.setItem('chatMessages', JSON.stringify(messages));
  }
}

function loadMessages() {
  messages.forEach(msg => {
    addMessage(msg.text, msg.sender, false, msg.sender === 'bot');
  });
}

function showTyping() {
  const typingBubble = document.createElement('div');
  typingBubble.classList.add('message', 'bot', 'typing');
  typingBubble.textContent = 'Typing...';
  chat.appendChild(typingBubble);
  chat.scrollTop = chat.scrollHeight;
  return typingBubble;
}

function removeTyping(typingElem) {
  if (typingElem) chat.removeChild(typingElem);
}

loadMessages();

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const userMessage = input.value.trim();
  if (!userMessage) return;

  addMessage(userMessage, 'user');
  input.value = '';
  input.disabled = true;
  sendBtn.disabled = true;

  const typingBubble = showTyping();

  try {
    const response = await fetch('http://127.0.0.1:8000/respond', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: messages.map(m => m.text).concat(userMessage) }),
    });

    if (!response.ok) throw new Error(`Error: ${response.statusText}`);

    const data = await response.json();

    removeTyping(typingBubble);

    if (data.reply) {
      addMessage(data.reply, 'bot', true, true);
      if (data.high_interest) {
        addMessage("⚡️ Looks like you're really interested! We'll get back to you soon.", 'bot');
      }
    } else {
      addMessage("Hmm, I don't have a response for that.", 'bot');
    }
  } catch (err) {
    removeTyping(typingBubble);
    addMessage("Oops, something went wrong. Try again later.", 'bot');
    console.error(err);
  } finally {
    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
  }
});

clearBtn.addEventListener('click', () => {
  chat.innerHTML = '';
  messages.length = 0;
  localStorage.removeItem('chatMessages');
  input.focus();
});
