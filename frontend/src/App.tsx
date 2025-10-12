import PRInputForm from "./components/PRInputForm";

function App() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white shadow-lg p-6 rounded-2xl">
        <h1 className="text-2xl font-bold mb-4">AI Code Review Assistant 🚀</h1>
        <PRInputForm />
      </div>
    </div>
  );
}

export default App;
