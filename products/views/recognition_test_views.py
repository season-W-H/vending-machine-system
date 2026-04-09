from django.shortcuts import render


def recognition_test_view(request):
    """
    商品识别测试页面视图
    """
    return render(request, 'recognition_test.html')