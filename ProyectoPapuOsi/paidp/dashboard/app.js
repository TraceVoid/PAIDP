import React, { useState } from "react";
import axios from "axios";

function App() {
  const [text, setText] = useState("");
  const [response, setResponse] = useState("");

  const analyze = async () => {
    const res = await axios.post("http://localhost:8000/analyze", {
      text: text
    });
    setResponse(JSON.stringify(res.data));
  };

  return (
    <div>
      <h1>PAIDP Dashboard</h1>
      <textarea onChange={e => setText(e.target.value)} />
      <button onClick={analyze}>Analyze</button>
      <pre>{response}</pre>
    </div>
  );
}

export default App;
