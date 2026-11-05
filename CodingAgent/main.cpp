#include <iostream>
#include <string>
#include <vector>

int add(int a, int b) {
    return a + b;
}

int multiply(int a, int b) {
    return a * b;
}

double average(const std::vector<int>& numbers) {
    if (numbers.empty()) {
        return 0.0;
    }

    int sum = 0;
    for (int n : numbers) {
        sum += n;
    }
    return static_cast<double>(sum) / numbers.size();
}

int findMax(const std::vector<int>& numbers) {
    int maxValue = numbers[0];
    for (size_t i = 1; i < numbers.size(); ++i) {
        if (numbers[i] > maxValue) {
            maxValue = numbers[i];
        }
    }
    return maxValue;
}

bool isEven(int n) {
    return n % 2 == 0;
}

std::string greet(const std::string& name) {
    return "Hello, " + name + "!";
}

int main() {
    std::vector<int> numbers = {4, 8, 15, 16, 23, 42};

    std::cout << greet("World") << std::endl;
    std::cout << "3 + 5 = " << add(3, 5) << std::endl;
    std::cout << "4 * 6 = " << multiply(4, 6) << std::endl;
    std::cout << "Average: " << average(numbers) << std::endl;
    std::cout << "Max: " << findMax(numbers) << std::endl;
    std::cout << "Is 10 even? " << (isEven(10) ? "yes" : "no") << std::endl;

    return 0;
}
