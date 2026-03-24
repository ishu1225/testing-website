function QuestionCard({ question, index, selectedOption, onAnswerChange }) {
  const options = [
    { key: 'A', label: question.optionA },
    { key: 'B', label: question.optionB },
    { key: 'C', label: question.optionC },
    { key: 'D', label: question.optionD },
  ]

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="mb-3 font-medium text-slate-800">
        Q{index + 1}. {question.questionText}
      </p>
      <div className="grid gap-2">
        {options.map((option) => (
          <label
            key={option.key}
            className="flex min-h-12 cursor-pointer items-center gap-3 rounded-lg border border-slate-200 px-3 py-3 hover:bg-slate-50"
          >
            <input
              type="radio"
              name={`question-${question.id}`}
              value={option.key}
              checked={selectedOption === option.key}
              onChange={() => onAnswerChange(question.id, option.key)}
              className="h-4 w-4"
            />
            <span className="text-sm sm:text-base">
              {option.key}. {option.label}
            </span>
          </label>
        ))}
      </div>
    </div>
  )
}

export default QuestionCard
