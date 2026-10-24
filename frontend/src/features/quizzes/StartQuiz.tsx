import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { buttonClass } from '../../ui/primitives'
import { startAttempt } from './api'
import '../../styles/quiz.css'

/** Creates the attempt once, then moves to it (so a reload of the quiz never starts another one). */
export function StartQuiz() {
  const quizId = Number(useParams().quizId)
  const fresh = useSearchParams()[0].get('fresh') === '1'
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return // StrictMode runs effects twice in development
    started.current = true
    startAttempt(quizId, fresh)
      .then(a => navigate(`/quiz-attempts/${a.id}`, { replace: true, state: { fellBack: a.fell_back } }))
      .catch(e => setError((e as Error).message))
  }, [quizId, fresh, navigate])

  return (
    <div className="generation-state" aria-busy={!error}>
      {error ? (
        <>
          <h1>We couldn’t start this quiz</h1>
          <p>{error}</p>
          <div><Link className={buttonClass('secondary')} to="/subjects">Back to subjects</Link></div>
        </>
      ) : <p>Starting your quiz…</p>}
    </div>
  )
}
