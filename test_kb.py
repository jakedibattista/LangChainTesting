from knowledge_base import KnowledgeBase
import os

def main():
    # Initialize knowledge base
    kb = KnowledgeBase()
    
    # Create a test document
    with open('test.txt', 'w') as f:
        f.write("""
        Artificial Intelligence (AI) is the simulation of human intelligence by machines.
        Machine Learning is a subset of AI that enables systems to learn from data.
        Deep Learning is a type of Machine Learning that uses neural networks with multiple layers.
        """)
    
    # Add document to knowledge base
    print("Adding document to knowledge base...")
    kb.add_document('test.txt')
    
    # Test search functionality
    print("\nTesting search...")
    query = "What is machine learning?"
    results = kb.search(query)
    
    print(f"\nResults for query: '{query}'")
    for doc in results:
        print(f"\nRelevant text: {doc.page_content}")
    
    # Clean up test file
    os.remove('test.txt')

if __name__ == "__main__":
    main() 