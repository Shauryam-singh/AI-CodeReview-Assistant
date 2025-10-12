import axios from "axios";

const API_URL = "http://127.0.0.1:8000";

export const analyzeRepo = async (repoUrl: string) => {
  const response = await axios.get(`${API_URL}/analyze`, {
    params: { repo_url: repoUrl },
  });
  return response.data;
};
