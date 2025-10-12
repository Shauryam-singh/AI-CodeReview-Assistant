import axios from "axios";

const API = axios.create({ baseURL: "http://127.0.0.1:8000" });

export const analyzeRepo = async (url: string) => {
  const res = await API.get(`/analyze?repo_url=${encodeURIComponent(url)}`);
  return res.data;
};
