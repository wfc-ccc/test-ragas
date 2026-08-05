from src.llm import create_deepseek_llm
import pytest
class TestLLM:

    @pytest.mark.smoke
    def test_llm(self):
        llm = create_deepseek_llm()
        response = llm.invoke('hello,你是什么大模型')
        print(response.content)
        assert True

