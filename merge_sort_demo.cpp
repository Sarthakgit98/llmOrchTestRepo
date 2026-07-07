/**
 * merge_sort_demo.cpp
 * 
 * A demonstration of the merge sort algorithm in C++.
 * This file contains both a recursive and an iterative implementation,
 * along with helper utilities for testing and visualization.
 */

#include <iostream>
#include <vector>
#include <algorithm>
#include <cassert>
#include <chrono>
#include <random>

// ---------------------------------------------------------------------------
// Recursive Merge Sort
// ---------------------------------------------------------------------------

/**
 * Merges two sorted subarrays [left..mid] and [mid+1..right] in-place using a
 * temporary buffer.
 */
static void mergeRecursive(std::vector<int>& arr, int left, int mid, int right) {
    // Determine sizes of the two halves
    int n1 = mid - left + 1;
    int n2 = right - mid;

    // Temporary arrays
    std::vector<int> L(n1);
    std::vector<int> R(n2);

    // Copy data into temp arrays
    for (int i = 0; i < n1; ++i) L[i] = arr[left + i];
    for (int j = 0; j < n2; ++j) R[j] = arr[mid + 1 + j];

    // Merge the temp arrays back into arr[left..right]
    int i = 0, j = 0, k = left;
    while (i < n1 && j < n2) {
        if (L[i] <= R[j]) {
            arr[k++] = L[i++];
        } else {
            arr[k++] = R[j++];
        }
    }

    // Copy any remaining elements of L[]
    while (i < n1) arr[k++] = L[i++];

    // Copy any remaining elements of R[]
    while (j < n2) arr[k++] = R[j++];
}

/**
 * Recursively sorts arr[left..right] using the classic divide-and-conquer
 * merge sort algorithm.
 *
 * Time Complexity:  O(n log n) in all cases.
 * Space Complexity: O(n) auxiliary (due to temporary arrays).
 * Stable:           Yes.
 */
static void mergeSortRecursiveHelper(std::vector<int>& arr, int left, int right) {
    if (left >= right) return;

    int mid = left + (right - left) / 2;

    // Sort first and second halves
    mergeSortRecursiveHelper(arr, left, mid);
    mergeSortRecursiveHelper(arr, mid + 1, right);

    // Merge the sorted halves
    mergeRecursive(arr, left, mid, right);
}

void mergeSort(std::vector<int>& arr) {
    if (arr.empty()) return;
    mergeSortRecursiveHelper(arr, 0, static_cast<int>(arr.size()) - 1);
}


// ---------------------------------------------------------------------------
// Iterative (Bottom-Up) Merge Sort
// ---------------------------------------------------------------------------

/**
 * Merges two sorted subarrays using the same logic as the recursive version
 * but driven by a bottom-up width loop.
 */
static void mergeIterative(std::vector<int>& arr, int left, int mid, int right) {
    int n1 = mid - left + 1;
    int n2 = right - mid;

    std::vector<int> L(n1), R(n2);
    for (int i = 0; i < n1; ++i) L[i] = arr[left + i];
    for (int j = 0; j < n2; ++j) R[j] = arr[mid + 1 + j];

    int i = 0, j = 0, k = left;
    while (i < n1 && j < n2) {
        arr[k++] = (L[i] <= R[j]) ? L[i++] : R[j++];
    }
    while (i < n1) arr[k++] = L[i++];
    while (j < n2) arr[k++] = R[j++];
}

/**
 * Sorts arr in non-decreasing order using an iterative (bottom-up) merge sort.
 * This avoids recursion overhead and can be useful for embedded or
 * stack-constrained environments.
 *
 * Time Complexity:  O(n log n) in all cases.
 * Space Complexity: O(n) auxiliary.
 * Stable:           Yes.
 */
void mergeSortIterative(std::vector<int>& arr) {
    int n = static_cast<int>(arr.size());
    if (n <= 1) return;

    // Bottom-up: double the subarray width each pass
    for (int width = 1; width < n; width *= 2) {
        for (int left = 0; left < n - 1; left += 2 * width) {
            int mid   = std::min(left + width - 1, n - 1);
            int right = std::min(left + 2 * width - 1, n - 1);

            if (mid < right) {
                mergeIterative(arr, left, mid, right);
            }
        }
    }
}


// ---------------------------------------------------------------------------
// Utility functions
// ---------------------------------------------------------------------------

/** Prints the contents of a vector to stdout. */
void printArray(const std::vector<int>& arr, const std::string& label = "") {
    if (!label.empty()) std::cout << label << ": ";
    std::cout << "[";
    for (size_t i = 0; i < arr.size(); ++i) {
        std::cout << arr[i];
        if (i + 1 < arr.size()) std::cout << ", ";
    }
    std::cout << "]\n";
}

/** Returns true if the vector is sorted in non-decreasing order. */
bool isSorted(const std::vector<int>& arr) {
    return std::is_sorted(arr.begin(), arr.end());
}

/** Generates a vector of n random integers in the range [lo, hi]. */
std::vector<int> generateRandomArray(int n, int lo = 1, int hi = 1000) {
    static std::mt19937 rng(42); // fixed seed for reproducibility
    std::uniform_int_distribution<int> dist(lo, hi);
    std::vector<int> arr(n);
    for (auto& v : arr) v = dist(rng);
    return arr;
}


// ---------------------------------------------------------------------------
// Benchmark helper
// ---------------------------------------------------------------------------

/**
 * Measures the execution time of a sorting function and prints the result.
 * The sorting function must have the signature: void(std::vector<int>&)
 */
using SortFn = void(*)(std::vector<int>&);

void benchmark(SortFn sortFn, const std::string& name, const std::vector<int>& original) {
    std::vector<int> arr = original; // copy so each benchmark starts fresh
    auto start = std::chrono::high_resolution_clock::now();
    sortFn(arr);
    auto end = std::chrono::high_resolution_clock::now();

    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
    std::cout << "  " << name << ": " << duration << " µs"
              << (isSorted(arr) ? " ✓" : " ✗ FAILED") << "\n";
}


// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void runTests() {
    std::cout << "--- Running unit tests ---\n";

    // Edge cases
    {
        std::vector<int> empty;
        mergeSort(empty);
        assert(empty.empty());

        std::vector<int> single = {7};
        mergeSort(single);
        assert(single == std::vector<int>{7});

        std::vector<int> two = {5, 3};
        mergeSort(two);
        assert((two == std::vector<int>{3, 5}));
    }

    // Already sorted
    {
        std::vector<int> sorted = {1, 2, 3, 4, 5};
        mergeSort(sorted);
        assert(isSorted(sorted));
    }

    // Reverse sorted
    {
        std::vector<int> reversed = {9, 7, 5, 3, 1};
        mergeSort(reversed);
        assert(isSorted(reversed));
    }

    // Duplicates
    {
        std::vector<int> dup = {4, 2, 4, 2, 4, 1};
        mergeSort(dup);
        assert(isSorted(dup));
    }

    // Large random (both implementations should match)
    {
        auto big = generateRandomArray(5000);
        std::vector<int> arr1 = big;
        std::vector<int> arr2 = big;

        mergeSort(arr1);
        mergeSortIterative(arr2);
        assert(isSorted(arr1) && isSorted(arr2));
        assert(arr1 == arr2);
    }

    std::cout << "  All unit tests passed ✓\n\n";
}


// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

int main() {
    // Small demonstration
    std::vector<int> demo = {38, 27, 43, 3, 9, 82, 10};
    printArray(demo, "Original        ");
    mergeSort(demo);
    printArray(demo, "Sorted (rec)    ");

    std::cout << "\n";

    // Iterative demo
    std::vector<int> demo2 = {38, 27, 43, 3, 9, 82, 10};
    printArray(demo2, "Original        ");
    mergeSortIterative(demo2);
    printArray(demo2, "Sorted (iter)   ");

    std::cout << "\n";

    // Run correctness tests
    runTests();

    // Performance benchmark
    std::cout << "--- Performance benchmark (n=100000) ---\n";
    auto largeArray = generateRandomArray(100000);

    benchmark(mergeSort,          "Recursive merge sort  ", largeArray);
    benchmark(mergeSortIterative, "Iterative merge sort  ", largeArray);
    benchmark([](std::vector<int>& a) { std::sort(a.begin(), a.end()); },
              "std::sort (reference) ", largeArray);

    return 0;
}
